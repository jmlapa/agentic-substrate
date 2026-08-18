import json
from unittest.mock import AsyncMock

import pytest

from src.kernel.infrastructure.redis_job_queue import RedisJobQueue
from src.modules.knowledge.domain.value_objects.job_task import JobTask


@pytest.mark.asyncio
async def test_redis_job_queue_enqueue_and_dequeue() -> None:
    mock_redis = AsyncMock()
    queue = RedisJobQueue(client=mock_redis)

    task = JobTask(id="task-1", queue_name="ocr_queue", payload={"page": 1})

    # Test enqueue
    await queue.enqueue("ocr_queue", task)
    assert mock_redis.rpush.called
    call_args = mock_redis.rpush.call_args[0]
    assert call_args[0] == "queue:ocr_queue"

    # Test dequeue
    serialized = json.dumps(task.model_dump())
    mock_redis.blpop.return_value = ("queue:ocr_queue", serialized)

    dequeued = await queue.dequeue("ocr_queue", timeout=1.0)
    assert dequeued is not None
    assert dequeued.id == "task-1"
    assert dequeued.payload == {"page": 1}

    # Test qsize
    mock_redis.llen.return_value = 5
    size = await queue.qsize("ocr_queue")
    assert size == 5

    # Test clear
    await queue.clear("ocr_queue")
    mock_redis.delete.assert_called_with("queue:ocr_queue")
