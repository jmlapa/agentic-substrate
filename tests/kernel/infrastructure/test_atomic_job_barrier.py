import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import redis.asyncio as aioredis

from src.kernel.infrastructure.atomic_job_barrier import AtomicJobBarrier


@pytest.mark.asyncio
async def test_init_barrier_mocked() -> None:
    mock_client = MagicMock()
    mock_client.hset = AsyncMock()
    mock_client.expire = AsyncMock()

    barrier = AtomicJobBarrier(client=mock_client)
    doc_id = uuid4()
    await barrier.init_barrier(doc_id=doc_id, total_chunks=5, step="ocr", ttl_seconds=3600)

    mock_client.hset.assert_awaited_once_with(
        f"barrier:{doc_id}:ocr",
        mapping={"total": "5", "completed": "0"},
    )
    mock_client.expire.assert_awaited_once_with(f"barrier:{doc_id}:ocr", 3600)


@pytest.mark.asyncio
async def test_increment_and_check_mocked() -> None:
    mock_client = MagicMock()
    mock_client.hget = AsyncMock(return_value="3")

    barrier = AtomicJobBarrier(client=mock_client)
    doc_id = uuid4()

    # 1st call: returns 1 != 3 -> False
    mock_client.hincrby = AsyncMock(return_value=1)
    res1 = await barrier.increment_and_check(doc_id, step="graph")
    assert res1 is False

    # 2nd call: returns 2 != 3 -> False
    mock_client.hincrby = AsyncMock(return_value=2)
    res2 = await barrier.increment_and_check(doc_id, step="graph")
    assert res2 is False

    # 3rd call: returns 3 == 3 -> True (single winner!)
    mock_client.hincrby = AsyncMock(return_value=3)
    res3 = await barrier.increment_and_check(doc_id, step="graph")
    assert res3 is True

    # 4th call (retry/duplicate): returns 4 != 3 -> False
    mock_client.hincrby = AsyncMock(return_value=4)
    res4 = await barrier.increment_and_check(doc_id, step="graph")
    assert res4 is False


@pytest.mark.asyncio
async def test_get_progress_and_reset_mocked() -> None:
    mock_client = MagicMock()
    mock_client.hgetall = AsyncMock(return_value={"completed": "2", "total": "5"})
    mock_client.delete = AsyncMock()

    barrier = AtomicJobBarrier(client=mock_client)
    doc_id = uuid4()

    completed, total = await barrier.get_progress(doc_id, step="ocr")
    assert completed == 2
    assert total == 5

    await barrier.reset(doc_id, step="ocr")
    mock_client.delete.assert_awaited_once_with(f"barrier:{doc_id}:ocr")


@pytest.mark.asyncio
async def test_barrier_live_concurrency_single_winner() -> None:
    """Verifica atomicidade e garantia de vencedor único concorrente no Redis real (porta 6381)."""
    try:
        client = aioredis.Redis.from_url("redis://localhost:6381/0", decode_responses=True)
        await client.ping()
    except Exception:
        pytest.skip("Redis live container não está disponível na porta 6381")

    barrier = AtomicJobBarrier(client=client)
    doc_id = uuid4()
    total_workers = 20

    try:
        await barrier.init_barrier(doc_id, total_chunks=total_workers, step="gather")

        async def worker_task() -> bool:
            # Simula pequeno jitter
            await asyncio.sleep(0.005)
            return await barrier.increment_and_check(doc_id, step="gather")

        # Dispara 20 workers simultaneamente
        tasks = [worker_task() for _ in range(total_workers)]
        results = await asyncio.gather(*tasks)

        # Exatamente um worker deve receber True
        assert results.count(True) == 1
        assert results.count(False) == total_workers - 1

        # Verifica progresso final
        completed, total = await barrier.get_progress(doc_id, step="gather")
        assert completed == total_workers
        assert total == total_workers

    finally:
        await barrier.reset(doc_id, step="gather")
        await getattr(client, "aclose", client.close)()
