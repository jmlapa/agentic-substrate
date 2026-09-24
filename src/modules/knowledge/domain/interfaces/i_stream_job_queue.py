from typing import Protocol, runtime_checkable

from src.modules.knowledge.domain.value_objects.job_task import JobTask


@runtime_checkable
class IStreamJobQueue(Protocol):
    """
    Protocolo de mensageria distribuída baseada em Redis Streams.
    Oferece entrega At-Least-Once com grupos de consumidores, confirmação atômica
    e recuperação de tarefas pendentes ou trabalhadores interrompidos via lease/autoclaim.
    """

    async def publish_task(
        self, stream_name: str, task: JobTask, maxlen: int | None = None
    ) -> str: ...

    async def consume_tasks(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 2000,
    ) -> list[tuple[str, JobTask]]: ...

    async def ack_task(self, stream_name: str, group_name: str, message_id: str) -> bool: ...

    async def claim_stale_tasks(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        min_idle_time_ms: int = 60000,
        count: int = 10,
    ) -> list[tuple[str, JobTask]]: ...

    async def ensure_consumer_group(self, stream_name: str, group_name: str) -> None: ...

    async def stream_len(self, stream_name: str) -> int: ...
