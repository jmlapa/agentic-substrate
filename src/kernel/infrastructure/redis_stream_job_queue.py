import json
from typing import Any

from src.modules.knowledge.domain.interfaces.i_stream_job_queue import IStreamJobQueue
from src.modules.knowledge.domain.value_objects.job_task import JobTask


class RedisStreamJobQueue(IStreamJobQueue):
    """
    Fila distribuída baseada em Redis Streams com semântica At-Least-Once.
    Utiliza XADD para publicação, XREADGROUP para consumo por consumer groups,
    XACK para confirmação e XAUTOCLAIM para recuperação de tarefas de workers caídos.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    async def ensure_consumer_group(self, stream_name: str, group_name: str) -> None:
        """Cria o grupo de consumidores caso ainda não exista (idempotente)."""
        try:
            await self._client.xgroup_create(
                name=stream_name,
                groupname=group_name,
                id="0",
                mkstream=True,
            )
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def publish_task(self, stream_name: str, task: JobTask, maxlen: int | None = None) -> str:
        """Publica uma tarefa no Redis Stream usando XADD."""
        task_data = json.dumps(task.model_dump(), ensure_ascii=False)
        fields = {"task_id": task.id, "payload": task_data}
        res = await self._client.xadd(
            name=stream_name,
            fields=fields,
            id="*",
            maxlen=maxlen,
            approximate=True,
        )
        return res.decode("utf-8") if isinstance(res, bytes) else str(res)

    async def consume_tasks(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 2000,
    ) -> list[tuple[str, JobTask]]:
        """Consome mensagens do stream pelo grupo de consumidores via XREADGROUP."""
        await self.ensure_consumer_group(stream_name, group_name)
        streams = {stream_name: ">"}
        res = await self._client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams=streams,
            count=count,
            block=block_ms,
        )
        if not res:
            return []

        tasks: list[tuple[str, JobTask]] = []
        for stream_entry in res:
            messages = stream_entry[1]
            for msg_id, raw_fields in messages:
                id_str = msg_id.decode("utf-8") if isinstance(msg_id, bytes) else str(msg_id)
                task = self._deserialize_task(raw_fields)
                if task is not None:
                    tasks.append((id_str, task))
        return tasks

    async def ack_task(self, stream_name: str, group_name: str, message_id: str) -> bool:
        """Confirma o processamento de uma mensagem via XACK."""
        res = await self._client.xack(stream_name, group_name, message_id)
        return int(res) > 0

    async def claim_stale_tasks(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        min_idle_time_ms: int = 60000,
        count: int = 10,
    ) -> list[tuple[str, JobTask]]:
        """
        Reatribui mensagens pendentes há mais de min_idle_time_ms
        para este consumidor via XAUTOCLAIM.
        """
        await self.ensure_consumer_group(stream_name, group_name)
        res = await self._client.xautoclaim(
            name=stream_name,
            groupname=group_name,
            consumername=consumer_name,
            min_idle_time=min_idle_time_ms,
            start_id="0-0",
            count=count,
        )
        if not res or len(res) < 2:
            return []

        messages = res[1]
        claimed: list[tuple[str, JobTask]] = []
        for msg_id, raw_fields in messages:
            id_str = msg_id.decode("utf-8") if isinstance(msg_id, bytes) else str(msg_id)
            task = self._deserialize_task(raw_fields)
            if task is not None:
                claimed.append((id_str, task))
        return claimed

    async def stream_len(self, stream_name: str) -> int:
        """Retorna o comprimento atual do stream via XLEN."""
        res = await self._client.xlen(stream_name)
        return int(res)

    def _deserialize_task(self, raw_fields: dict[Any, Any]) -> JobTask | None:
        try:
            payload_field: Any = None
            if "payload" in raw_fields:
                payload_field = raw_fields["payload"]
            elif b"payload" in raw_fields:
                payload_field = raw_fields[b"payload"]

            if payload_field is None:
                return None

            if isinstance(payload_field, bytes):
                payload_field = payload_field.decode("utf-8")
            data = json.loads(payload_field) if isinstance(payload_field, str) else payload_field
            return JobTask.model_validate(data)
        except Exception:
            return None
