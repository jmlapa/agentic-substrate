import asyncio
from collections import defaultdict

from src.modules.knowledge.domain.interfaces.i_job_queue import IJobQueue
from src.modules.knowledge.domain.value_objects.job_task import JobTask


class InMemoryJobQueue(IJobQueue):
    """
    Implementação em memória de fila de jobs assíncrona baseada em asyncio.Queue.
    Utilizada em testes unitários e ambientes de desenvolvimento local sem Redis.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[JobTask]] = defaultdict(asyncio.Queue)

    async def enqueue(self, queue_name: str, task: JobTask) -> None:
        await self._queues[queue_name].put(task)

    async def dequeue(self, queue_name: str, timeout: float = 1.0) -> JobTask | None:
        q = self._queues[queue_name]
        try:
            return await asyncio.wait_for(q.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def qsize(self, queue_name: str) -> int:
        return self._queues[queue_name].qsize()

    async def clear(self, queue_name: str) -> None:
        q = self._queues[queue_name]
        while not q.empty():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                break
