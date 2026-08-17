from typing import Any

import httpx
import pytest

from src.modules.knowledge.domain.interfaces.i_embedding_service import (
    IEmbeddingService,
)
from src.modules.knowledge.infrastructure.adapters.gemini_embedding_adapter import (
    GeminiEmbeddingAdapter,
)


@pytest.mark.asyncio
async def test_gemini_embedding_adapter_implements_protocol() -> None:
    adapter = GeminiEmbeddingAdapter(api_key="fake-key")
    assert isinstance(adapter, IEmbeddingService)


@pytest.mark.asyncio
async def test_gemini_embedding_adapter_embed_texts_success() -> None:
    captured_requests: list[dict[str, Any]] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        import json

        body: dict[str, Any] = json.loads(request.read().decode("utf-8"))
        captured_requests.append(body)
        return httpx.Response(
            status_code=200,
            json={
                "embeddings": [
                    {"values": [0.1] * 768},
                    {"values": [0.2] * 768},
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiEmbeddingAdapter(
            api_key="test-api-key",
            dimension=768,
            http_client=client,
        )
        results = await adapter.embed_texts(
            texts=["Text chunk 1", "Text chunk 2"],
            titles=["Doc 1", "Doc 2"],
        )

    assert len(results) == 2
    assert len(results[0]) == 768
    assert len(captured_requests) == 1
    req_body = captured_requests[0]
    requests_list: list[dict[str, Any]] = req_body["requests"]
    assert len(requests_list) == 2
    assert requests_list[0]["content"]["parts"][0]["text"] == "title: Doc 1 | text: Text chunk 1"
    assert requests_list[0]["output_dimensionality"] == 768


@pytest.mark.asyncio
async def test_gemini_embedding_adapter_embed_query_success() -> None:
    captured_requests: list[dict[str, Any]] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        import json

        body: dict[str, Any] = json.loads(request.read().decode("utf-8"))
        captured_requests.append(body)
        return httpx.Response(
            status_code=200,
            json={"embeddings": [{"values": [0.5] * 768}]},
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiEmbeddingAdapter(
            api_key="test-api-key",
            dimension=768,
            http_client=client,
        )
        query_vector = await adapter.embed_query("find relevant docs")

    assert len(query_vector) == 768
    assert len(captured_requests) == 1
    req_body = captured_requests[0]
    requests_list: list[dict[str, Any]] = req_body["requests"]
    assert (
        requests_list[0]["content"]["parts"][0]["text"]
        == "task: search result | query: find relevant docs"
    )


@pytest.mark.asyncio
async def test_gemini_embedding_adapter_retry_on_429_success() -> None:
    attempts = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                status_code=429,
                json={"error": {"message": "ResourceExhausted: rate limit exceeded"}},
            )
        return httpx.Response(
            status_code=200,
            json={"embeddings": [{"values": [0.3] * 768}]},
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiEmbeddingAdapter(
            api_key="test-api-key",
            dimension=768,
            max_retries=3,
            base_delay=0.01,
            max_delay=0.05,
            http_client=client,
        )
        results = await adapter.embed_texts(["Retry text"])

    assert len(results) == 1
    assert attempts == 2


@pytest.mark.asyncio
async def test_gemini_embedding_adapter_exhausted_retries_raises() -> None:
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=429,
            json={"error": {"message": "ResourceExhausted"}},
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiEmbeddingAdapter(
            api_key="test-api-key",
            max_retries=2,
            base_delay=0.01,
            max_delay=0.02,
            http_client=client,
        )
        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            await adapter.embed_texts(["Text"])
