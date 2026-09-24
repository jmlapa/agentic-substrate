from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import redis.asyncio as aioredis

from src.kernel.infrastructure.redis_stream_job_queue import RedisStreamJobQueue
from src.modules.knowledge.domain.value_objects.job_task import JobTask


@pytest.mark.asyncio
async def test_publish_and_consume_mocked() -> None:
    mock_client = MagicMock()
    mock_client.xgroup_create = AsyncMock()
    mock_client.xadd = AsyncMock(return_value="1710000000000-0")
    mock_client.xack = AsyncMock(return_value=1)
    mock_client.xlen = AsyncMock(return_value=1)

    task_payload = {
        "id": "task-123",
        "queue_name": "jobs:ocr",
        "payload": {"doc_id": str(uuid4()), "page_index": 0},
    }
    raw_message = (
        "1710000000000-0",
        {
            "task_id": "task-123",
            "payload": '{"id": "task-123", "queue_name": "jobs:ocr", "payload": {"doc_id": "xyz"}}',
        },
    )
    mock_client.xreadgroup = AsyncMock(return_value=[["stream:ocr", [raw_message]]])

    queue = RedisStreamJobQueue(client=mock_client)

    task = JobTask.model_validate(task_payload)
    msg_id = await queue.publish_task("stream:ocr", task)
    assert msg_id == "1710000000000-0"
    mock_client.xadd.assert_awaited_once()

    consumed = await queue.consume_tasks("stream:ocr", "ocr_group", "worker-1", count=1)
    assert len(consumed) == 1
    m_id, c_task = consumed[0]
    assert m_id == "1710000000000-0"
    assert c_task.id == "task-123"

    acked = await queue.ack_task("stream:ocr", "ocr_group", m_id)
    assert acked is True
    mock_client.xack.assert_awaited_once_with("stream:ocr", "ocr_group", m_id)


@pytest.mark.asyncio
async def test_ensure_consumer_group_swallows_busygroup() -> None:
    mock_client = MagicMock()
    mock_client.xgroup_create = AsyncMock(
        side_effect=Exception("BUSYGROUP Consumer Group name already exists")
    )

    queue = RedisStreamJobQueue(client=mock_client)
    # Should not raise exception
    await queue.ensure_consumer_group("stream:test", "test_group")


@pytest.mark.asyncio
async def test_claim_stale_tasks_mocked() -> None:
    mock_client = MagicMock()
    mock_client.xgroup_create = AsyncMock()
    raw_message = (
        "1710000000000-1",
        {
            "task_id": "task-999",
            "payload": '{"id": "task-999", "queue_name": "jobs:ocr", "payload": {}}',
        },
    )
    mock_client.xautoclaim = AsyncMock(return_value=["0-0", [raw_message], []])

    queue = RedisStreamJobQueue(client=mock_client)
    claimed = await queue.claim_stale_tasks(
        "stream:ocr", "ocr_group", "worker-2", min_idle_time_ms=5000
    )

    assert len(claimed) == 1
    msg_id, task = claimed[0]
    assert msg_id == "1710000000000-1"
    assert task.id == "task-999"


@pytest.mark.asyncio
async def test_redis_stream_job_queue_live_integration() -> None:
    """Verifica o ciclo completo At-Least-Once contra o container Redis real na porta 6381."""
    try:
        client = aioredis.Redis.from_url("redis://localhost:6381/0", decode_responses=True)
        await client.ping()
    except Exception:
        pytest.skip("Redis live container não está disponível na porta 6381")

    queue = RedisStreamJobQueue(client=client)
    stream_name = f"test:stream:{uuid4()}"
    group_name = "test_grp"
    consumer_1 = "worker_1"
    consumer_2 = "worker_2"

    try:
        task1 = JobTask(
            id="t1",
            queue_name=stream_name,
            payload={"doc_id": "d1", "page": 1},
        )
        msg_id1 = await queue.publish_task(stream_name, task1)
        assert msg_id1 is not None

        length = await queue.stream_len(stream_name)
        assert length >= 1

        # Consome com consumer_1
        consumed = await queue.consume_tasks(
            stream_name=stream_name,
            group_name=group_name,
            consumer_name=consumer_1,
            count=10,
            block_ms=500,
        )
        assert len(consumed) == 1
        rec_id, rec_task = consumed[0]
        assert rec_id == msg_id1
        assert rec_task.id == "t1"
        assert rec_task.payload == {"doc_id": "d1", "page": 1}

        # Simula recuperação de tarefa abandonada por consumer_2 com min_idle_time_ms=0
        stale = await queue.claim_stale_tasks(
            stream_name=stream_name,
            group_name=group_name,
            consumer_name=consumer_2,
            min_idle_time_ms=0,
            count=10,
        )
        assert len(stale) == 1
        stale_id, stale_task = stale[0]
        assert stale_id == msg_id1
        assert stale_task.id == "t1"

        # Confirma a tarefa (ACK)
        acked = await queue.ack_task(stream_name, group_name, msg_id1)
        assert acked is True

        # Nova tentativa de autoclaim não deve trazer nada pois já foi feito ACK
        stale_after_ack = await queue.claim_stale_tasks(
            stream_name=stream_name,
            group_name=group_name,
            consumer_name=consumer_2,
            min_idle_time_ms=0,
            count=10,
        )
        assert len(stale_after_ack) == 0

    finally:
        await client.delete(stream_name)
        await getattr(client, "aclose", client.close)()
