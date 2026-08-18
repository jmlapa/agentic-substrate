from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)
from src.modules.knowledge.infrastructure.adapters.deepseek_rag_synthesizer import (
    DeepSeekRagSynthesizer,
)


@pytest.mark.asyncio
async def test_deepseek_rag_synthesizer_empty_results() -> None:
    synthesizer = DeepSeekRagSynthesizer(api_key="test-key")
    answer = await synthesizer.synthesize_answer("Qual é a regra de ouro?", [])

    assert "Nenhum documento ou contexto relevante" in answer


@pytest.mark.asyncio
async def test_deepseek_rag_synthesizer_success() -> None:
    mock_http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    expected_content = (
        "- O limite de requisições é de 300 RPM [^chunk:chunk-123].\n"
        "- Política de isolamento ativo [^entidade:Concept:Seguranca]."
    )
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": expected_content,
                }
            }
        ]
    }
    mock_http_client.post.return_value = mock_response

    synthesizer = DeepSeekRagSynthesizer(
        api_key="test-key",
        model_name="deepseek/deepseek-v4-flash",
        http_client=mock_http_client,
    )

    results = [
        HybridSearchResult(
            parent_chunk_id="chunk-123",
            header_path="# Arquitetura > Limites",
            parent_content="Limite estrito de 300 RPM.",
            relevance_score=0.98,
            related_entities=[{"type": "Concept", "properties": {"name": "Seguranca"}}],
        )
    ]

    answer = await synthesizer.synthesize_answer(
        query="Qual o limite de RPM?",
        search_results=results,
    )

    assert "[^chunk:chunk-123]" in answer
    assert "[^entidade:Concept:Seguranca]" in answer
    mock_http_client.post.assert_awaited_once()

    # Check payload contents
    call_args = mock_http_client.post.await_args
    assert call_args is not None
    _, kwargs = call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert kwargs["headers"]["HTTP-Referer"] == "https://agentic-substrate.local"
    assert kwargs["headers"]["X-Title"] == "Agentic Substrate"
    payload = kwargs["json"]
    assert payload["model"] == "deepseek/deepseek-v4-flash"
    assert payload["temperature"] == 0.1
    assert "Limite estrito de 300 RPM." in payload["messages"][1]["content"]
    assert "chunk-123" in payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_deepseek_rag_synthesizer_http_error_graceful_fallback() -> None:
    mock_http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_http_client.post.side_effect = httpx.HTTPStatusError(
        "Rate limit exceeded",
        request=MagicMock(),
        response=MagicMock(status_code=429),
    )

    synthesizer = DeepSeekRagSynthesizer(
        api_key="test-key",
        http_client=mock_http_client,
    )

    results = [
        HybridSearchResult(
            parent_chunk_id="chunk-abc",
            header_path="",
            parent_content="Conteúdo de teste.",
            relevance_score=0.85,
            related_entities=[],
        )
    ]

    answer = await synthesizer.synthesize_answer(
        query="Pergunta?",
        search_results=results,
    )

    assert "Erro na comunicação com o LLM via OpenRouter" in answer
    assert "1 resultados disponíveis no inspetor" in answer
