import asyncio
import random
from typing import Any

import httpx

from src.modules.knowledge.domain.interfaces.i_embedding_service import (
    IEmbeddingService,
)


class GeminiEmbeddingAdapter(IEmbeddingService):
    """
    Adaptador de produção para Google Gemini API (`gemini-embedding-2`).
    Implementa:
      - Formatação de prompts oficial (title/text para indexação e task instruction para query)
      - Matryoshka Representation Learning (MRL) com output_dimensionality
      - Micro-batching assíncrono (até 100 itens por request)
      - Exponential backoff com full jitter para tolerância a HTTP 429 (ResourceExhausted) e 503
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        model_name: str = "models/gemini-embedding-2",
        dimension: int = 768,
        batch_size: int = 100,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_name = (
            model_name if model_name.startswith("models/") else f"models/{model_name}"
        )
        self._dimension = dimension
        self._batch_size = min(batch_size, 100)
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=60.0)

    async def _execute_with_retry(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        should_close = self._client is None
        client = await self._get_client()

        try:
            for attempt in range(self._max_retries + 1):
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code == 200:
                        data: dict[str, Any] = response.json()
                        return data

                    # Tratar 429 (Rate Limit / ResourceExhausted) ou 503 (Unavailable)
                    if response.status_code in (429, 503):
                        if attempt == self._max_retries:
                            msg = (
                                f"Gemini API rate limit exceeded after {self._max_retries} "
                                f"retries: HTTP {response.status_code} - {response.text}"
                            )
                            raise RuntimeError(msg)
                        # Exponential backoff com Full Jitter
                        delay = random.uniform(
                            0, min(self._max_delay, self._base_delay * (2**attempt))
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Erro fatal não recuperável
                    raise RuntimeError(
                        f"Gemini API error (HTTP {response.status_code}): {response.text}"
                    )
                except httpx.RequestError as e:
                    if attempt == self._max_retries:
                        raise RuntimeError(
                            f"Gemini API network error after {self._max_retries} retries: {e}"
                        ) from e
                    delay = random.uniform(0, min(self._max_delay, self._base_delay * (2**attempt)))
                    await asyncio.sleep(delay)
            raise RuntimeError("Gemini API max retries reached without response")
        finally:
            if should_close:
                await client.aclose()

    async def embed_texts(
        self,
        texts: list[str],
        titles: list[str] | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # Divide em micro-batches de até 100 itens
        for i in range(0, len(texts), self._batch_size):
            batch_texts = texts[i : i + self._batch_size]
            batch_requests: list[dict[str, Any]] = []

            for idx, text in enumerate(batch_texts):
                global_idx = i + idx
                title = titles[global_idx] if titles and global_idx < len(titles) else "none"
                formatted_text = f"title: {title} | text: {text}"
                req_item: dict[str, Any] = {
                    "model": self._model_name,
                    "content": {"parts": [{"text": formatted_text}]},
                }
                if self._dimension:
                    req_item["output_dimensionality"] = self._dimension
                batch_requests.append(req_item)

            payload = {"requests": batch_requests}
            endpoint = f"{self._model_name}:batchEmbedContents"
            data = await self._execute_with_retry(endpoint, payload)

            raw_embeddings = data.get("embeddings", [])
            for item in raw_embeddings:
                values = item.get("values", [])
                all_embeddings.append([float(v) for v in values])

        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        formatted_query = f"task: search result | query: {query}"
        req_item: dict[str, Any] = {
            "model": self._model_name,
            "content": {"parts": [{"text": formatted_query}]},
        }
        if self._dimension:
            req_item["output_dimensionality"] = self._dimension

        payload = {"requests": [req_item]}
        endpoint = f"{self._model_name}:batchEmbedContents"
        data = await self._execute_with_retry(endpoint, payload)

        raw_embeddings = data.get("embeddings", [])
        if not raw_embeddings:
            raise RuntimeError("Gemini API returned empty embeddings list for query")

        values = raw_embeddings[0].get("values", [])
        return [float(v) for v in values]
