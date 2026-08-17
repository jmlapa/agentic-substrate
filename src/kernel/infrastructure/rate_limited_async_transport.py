import asyncio
import random
from typing import Any

import httpx

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)


class RateLimitedAsyncTransport(httpx.AsyncBaseTransport):
    """
    Transporte HTTPX assíncrono com controle estrito de vazão e resiliência a 429.
    Intercepta 100% dos disparos de rede de agentes (incluindo retries internos e tool calls),
    consumindo cotas de RPM e TPM antes da transmissão física de bytes.
    """

    def __init__(
        self,
        rate_limiter: AsyncTokenBucketLimiter,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries_429: int = 5,
        base_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 30.0,
    ) -> None:
        self._limiter = rate_limiter
        self._transport = transport or httpx.AsyncHTTPTransport()
        self._max_retries_429 = max(0, max_retries_429)
        self._base_backoff = base_backoff_seconds
        self._max_backoff = max_backoff_seconds

    def _estimate_tokens(self, request: httpx.Request) -> int:
        if not request.content:
            return 100
        # Estimativa: 4 caracteres por token no payload JSON
        return max(1, len(request.content) // 4)

    def _get_retry_after(self, response: httpx.Response, attempt: int) -> float:
        retry_header = response.headers.get("retry-after")
        if retry_header:
            try:
                return max(0.1, float(retry_header))
            except ValueError:
                pass
        # Exponential backoff com full jitter
        backoff = float(min(self._max_backoff, self._base_backoff * (2**attempt)))
        jitter = float(random.uniform(0.0, backoff * 0.5))
        return float(backoff + jitter)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        estimated_tokens = self._estimate_tokens(request)
        attempts = 0

        while True:
            # 1. Aguarda autorização no limiter de RPM e TPM
            await self._limiter.acquire(estimated_tokens)

            # 2. Executa a requisição física
            response = await self._transport.handle_async_request(request)

            # 3. Tratamento de 429 (Too Many Requests)
            if response.status_code == 429 and attempts < self._max_retries_429:
                attempts += 1
                sleep_seconds = self._get_retry_after(response, attempts)
                await asyncio.sleep(sleep_seconds)
                continue

            return response

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> "RateLimitedAsyncTransport":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
