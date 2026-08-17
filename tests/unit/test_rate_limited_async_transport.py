import httpx
import pytest

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)
from src.kernel.infrastructure.rate_limited_async_transport import (
    RateLimitedAsyncTransport,
)


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = list(responses)
        self.call_count = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.call_count += 1
        if self._responses:
            return self._responses.pop(0)
        return httpx.Response(200, json={"status": "ok"}, request=request)


@pytest.mark.asyncio
async def test_rate_limited_transport_normal_request() -> None:
    limiter = AsyncTokenBucketLimiter(max_rpm=100, max_tpm=10_000)
    mock_transport = MockTransport([httpx.Response(200, json={"result": "success"})])

    transport = RateLimitedAsyncTransport(
        rate_limiter=limiter,
        transport=mock_transport,
    )

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post("https://api.example.com/data", json={"text": "hello world"})
        assert response.status_code == 200
        assert response.json() == {"result": "success"}
        assert mock_transport.call_count == 1
        assert limiter.current_rpm_usage == 1


@pytest.mark.asyncio
async def test_rate_limited_transport_429_retry() -> None:
    limiter = AsyncTokenBucketLimiter(max_rpm=100, max_tpm=10_000)
    # Primeiro retorno é 429, segundo é 200
    mock_transport = MockTransport(
        [
            httpx.Response(429, headers={"retry-after": "0.05"}),
            httpx.Response(200, json={"result": "recovered"}),
        ]
    )

    transport = RateLimitedAsyncTransport(
        rate_limiter=limiter,
        transport=mock_transport,
        max_retries_429=2,
        base_backoff_seconds=0.01,
    )

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://api.example.com/test")
        assert response.status_code == 200
        assert response.json() == {"result": "recovered"}
        assert mock_transport.call_count == 2
