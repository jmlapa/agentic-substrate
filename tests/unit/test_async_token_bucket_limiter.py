import asyncio
import time

import pytest

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)


@pytest.mark.asyncio
async def test_limiter_rpm_immediate_then_throttle() -> None:
    # 3 requisições por janela de 0.2 segundos
    limiter = AsyncTokenBucketLimiter(max_rpm=3, max_tpm=10_000, window_seconds=0.2)

    start = time.monotonic()
    await limiter.acquire(10)
    await limiter.acquire(10)
    await limiter.acquire(10)
    elapsed_first_three = time.monotonic() - start

    assert elapsed_first_three < 0.1
    assert limiter.current_rpm_usage == 3

    # A 4ª requisição deve aguardar a janela de 0.2s expirar
    await limiter.acquire(10)
    total_elapsed = time.monotonic() - start

    assert total_elapsed >= 0.18


@pytest.mark.asyncio
async def test_limiter_tpm_throttling() -> None:
    # 100 tokens por janela de 0.2 segundos
    limiter = AsyncTokenBucketLimiter(max_rpm=100, max_tpm=100, window_seconds=0.2)

    start = time.monotonic()
    await limiter.acquire(60)
    await limiter.acquire(30)
    # Total de tokens = 90

    assert time.monotonic() - start < 0.1
    assert limiter.current_tpm_usage == 90

    # Próxima requisição com 20 tokens ultrapassa 100 (90 + 20 = 110)
    await limiter.acquire(20)
    total_elapsed = time.monotonic() - start

    assert total_elapsed >= 0.18


@pytest.mark.asyncio
async def test_limiter_concurrency() -> None:
    limiter = AsyncTokenBucketLimiter(max_rpm=10, max_tpm=1000, window_seconds=0.3)

    async def worker(worker_id: int) -> int:
        await limiter.acquire(10)
        return worker_id

    # 10 requisições simultâneas
    results = await asyncio.gather(*(worker(i) for i in range(10)))
    assert len(results) == 10
    assert sorted(results) == list(range(10))
