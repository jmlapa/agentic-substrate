import json
from typing import Any

from src.modules.knowledge.domain.interfaces.i_job_queue import IJobQueue
from src.modules.knowledge.domain.value_objects.job_task import JobTask


class RedisJobQueue(IJobQueue):
    """
    Implementação de fila persistente no Redis utilizando LPUSH / BLPOP.
    Garante persistência atômica entre reinicializações de workers e containers.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def _get_key(self, queue_name: str) -> str:
        return f"queue:{queue_name}"

    async def enqueue(self, queue_name: str, task: JobTask) -> None:
        key = self._get_key(queue_name)
        data = json.dumps(task.model_dump(), ensure_ascii=False)
        await self._client.rpush(key, data)

    async def dequeue(self, queue_name: str, timeout: float = 1.0) -> JobTask | None:
        key = self._get_key(queue_name)
        timeout_int = max(1, int(timeout))
        res = await self._client.blpop([key], timeout=timeout_int)
        if not res:
            return None
        # blpop returns tuple (key, value)
        _, raw_val = res
        if isinstance(raw_val, bytes):
            raw_val = raw_val.decode("utf-8")
        data = json.loads(raw_val)
        return JobTask.model_validate(data)

    async def qsize(self, queue_name: str) -> int:
        key = self._get_key(queue_name)
        return int(await self._client.llen(key))

    async def clear(self, queue_name: str) -> None:
        key = self._get_key(queue_name)
        await self._client.delete(key)
