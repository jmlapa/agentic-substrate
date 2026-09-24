from typing import Any
from uuid import UUID


class AtomicJobBarrier:
    """
    Barreira atômica de coordenação Scatter-Gather baseada em Redis Hashes.
    Permite que múltiplos workers paralelos processem fragmentos (páginas OCR ou chunks de grafo)
    e garante que exatamente um worker (o último a concluir) seja o 'vencedor' responsável
    por consolidar os resultados e avançar a saga para o próximo estado.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def _get_key(self, doc_id: UUID, step: str) -> str:
        return f"barrier:{doc_id}:{step}"

    async def init_barrier(
        self,
        doc_id: UUID,
        total_chunks: int,
        step: str = "default",
        ttl_seconds: int = 86400,
    ) -> None:
        """Inicializa a barreira com o total de tarefas e contador zerado."""
        key = self._get_key(doc_id, step)
        mapping = {"total": str(total_chunks), "completed": "0"}
        await self._client.hset(key, mapping=mapping)
        await self._client.expire(key, ttl_seconds)

    async def increment_and_check(self, doc_id: UUID, step: str = "default") -> bool:
        """
        Incrementa atomicamente o contador de conclusões via HINCRBY.
        Retorna True exclusivamente para o worker que completa a última tarefa (completed == total).
        """
        key = self._get_key(doc_id, step)
        completed = await self._client.hincrby(key, "completed", 1)

        total_raw = await self._client.hget(key, "total")
        if total_raw is None:
            return False

        if isinstance(total_raw, bytes):
            total_raw = total_raw.decode("utf-8")
        total = int(total_raw)

        return int(completed) == total

    async def increment_and_status(
        self, doc_id: UUID, step: str = "default"
    ) -> tuple[bool, int, int]:
        """
        Incrementa atomicamente o contador via HINCRBY e retorna (is_last, completed, total).
        """
        key = self._get_key(doc_id, step)
        completed = await self._client.hincrby(key, "completed", 1)

        total_raw = await self._client.hget(key, "total")
        if total_raw is None:
            return (False, int(completed), 0)

        if isinstance(total_raw, bytes):
            total_raw = total_raw.decode("utf-8")
        total = int(total_raw)

        return (int(completed) == total, int(completed), total)

    async def get_progress(self, doc_id: UUID, step: str = "default") -> tuple[int, int]:
        """Retorna o progresso atual no formato (completed, total)."""
        key = self._get_key(doc_id, step)
        data = await self._client.hgetall(key)
        if not data:
            return (0, 0)

        def _parse(val: Any) -> int:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            return int(val) if val is not None else 0

        completed = _parse(data.get("completed") or data.get(b"completed"))
        total = _parse(data.get("total") or data.get(b"total"))
        return (completed, total)

    async def reset(self, doc_id: UUID, step: str = "default") -> None:
        """Remove a chave de barreira do Redis."""
        key = self._get_key(doc_id, step)
        await self._client.delete(key)
