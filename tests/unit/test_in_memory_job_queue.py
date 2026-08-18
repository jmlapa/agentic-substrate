import pytest

from src.kernel.infrastructure.in_memory_job_queue import InMemoryJobQueue
from src.modules.knowledge.domain.value_objects.job_task import JobTask


@pytest.mark.asyncio
async def test_in_memory_job_queue_enqueue_dequeue() -> None:
    queue = InMemoryJobQueue()
    queue_name = "test_queue"

    assert await queue.qsize(queue_name) == 0
    assert await queue.dequeue(queue_name, timeout=0.01) is None

    task1 = JobTask(id="1", queue_name=queue_name, payload={"page": 1})
    task2 = JobTask(id="2", queue_name=queue_name, payload={"page": 2})

    await queue.enqueue(queue_name, task1)
    await queue.enqueue(queue_name, task2)

    assert await queue.qsize(queue_name) == 2

    dequeued1 = await queue.dequeue(queue_name, timeout=0.1)
    assert dequeued1 is not None
    assert dequeued1.id == "1"

    dequeued2 = await queue.dequeue(queue_name, timeout=0.1)
    assert dequeued2 is not None
    assert dequeued2.id == "2"

    assert await queue.qsize(queue_name) == 0


@pytest.mark.asyncio
async def test_in_memory_job_queue_clear() -> None:
    queue = InMemoryJobQueue()
    queue_name = "test_queue"

    task = JobTask(id="1", queue_name=queue_name, payload={})
    await queue.enqueue(queue_name, task)
    assert await queue.qsize(queue_name) == 1

    await queue.clear(queue_name)
    assert await queue.qsize(queue_name) == 0
