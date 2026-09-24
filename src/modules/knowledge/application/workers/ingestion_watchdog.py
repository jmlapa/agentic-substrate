import asyncio
import logging
from uuid import UUID

import asyncpg

from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.reprocess_document.reprocess_document_request import (  # noqa: E501
    ReprocessDocumentRequest,
)
from src.modules.knowledge.application.use_cases.reprocess_document.reprocess_document_use_case import (  # noqa: E501
    ReprocessDocumentUseCase,
)

logger = logging.getLogger(__name__)


class IngestionWatchdog:
    """
    Serviço supervisor em background para auto-recuperação de documentos zumbis.
    Utiliza o índice parcial 'idx_attached_documents_zombie_recovery' para encontrar documentos
    estagnados em UPLOADED, PARSED ou CHUNKED há mais de 10 minutos sem heartbeat, adquire lease
    atômico condicional e reprocessa a partir dos checkpoints de disco ($0.00 de tokens adicionais).
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        reprocess_use_case: ReprocessDocumentUseCase,
        max_attempts: int = 3,
        threshold_minutes: int = 10,
        check_interval_seconds: int = 120,
    ) -> None:
        self._pool = pool
        self._reprocess_use_case = reprocess_use_case
        self._max_attempts = max_attempts
        self._threshold_minutes = threshold_minutes
        self._interval_seconds = check_interval_seconds
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def check_and_recover_stale_documents(self) -> list[UUID]:
        """Varre documentos zumbis com índice parcial e executa lease condicional atômico."""
        # 1. Busca documentos estagnados usando o índice parcial
        select_query = f"""
        SELECT id, kb_id, status, updated_at, recovery_attempt
        FROM attached_documents
        WHERE status IN ('UPLOADED', 'PARSED', 'CHUNKED')
          AND updated_at < NOW() - INTERVAL '{self._threshold_minutes} minutes'
          AND recovery_attempt < $1
        ORDER BY updated_at ASC
        LIMIT 50;
        """

        lease_query = """
        UPDATE attached_documents
        SET status = 'RECOVERING',
            recovery_attempt = recovery_attempt + 1,
            updated_at = NOW()
        WHERE id = $1
          AND status = $2
          AND updated_at = $3
        RETURNING id;
        """

        recovered_ids: list[UUID] = []

        async with self._pool.acquire() as conn:
            stale_rows = await conn.fetch(select_query, self._max_attempts)
            if not stale_rows:
                return []

            for row in stale_rows:
                doc_id: UUID = row["id"]
                kb_id: UUID = row["kb_id"]
                expected_status: str = row["status"]
                expected_updated_at = row["updated_at"]

                # 2. Lease atômico condicional (Optimistic Locking): garante que apenas 1 instância assume o documento  # noqa: E501
                acquired_row = await conn.fetchrow(
                    lease_query,
                    doc_id,
                    expected_status,
                    expected_updated_at,
                )

                if not acquired_row:
                    # Outro worker ou watchdog já assumiu ou o documento avançou
                    continue

                logger.info(
                    "IngestionWatchdog adquiriu lease para documento %s na KB %s (tentativa %s)",
                    doc_id,
                    kb_id,
                    row["recovery_attempt"] + 1,
                )

                # 3. Dispara reprocessamento durável reaproveitando checkpoints em disco
                req = ReprocessDocumentRequest(kb_id=kb_id, document_id=doc_id)
                res = await self._reprocess_use_case.execute(req)

                if isinstance(res, Ok):
                    recovered_ids.append(doc_id)
                    logger.info(
                        "Documento %s recuperado com sucesso pelo Watchdog.",
                        doc_id,
                    )
                elif isinstance(res, Err):
                    logger.error(
                        "Falha ao reprocessar documento %s pelo Watchdog: %s",
                        doc_id,
                        res.error.message,
                    )
                    # Se atingiu o limite de tentativas, marca como falha definitiva
                    if row["recovery_attempt"] + 1 >= self._max_attempts:
                        await conn.execute(
                            """
                            UPDATE attached_documents
                            SET status = 'FAILED',
                                error_step = 'WATCHDOG_MAX_RETRIES',
                                error_message = $1,
                                updated_at = NOW()
                            WHERE id = $2;
                            """,
                            f"Falha de recuperação após {self._max_attempts} tentativas: {res.error.message}",  # noqa: E501
                            doc_id,
                        )

        return recovered_ids

    async def start(self) -> None:
        """Inicia o ciclo contínuo do Watchdog."""
        self._running = True
        self._task = asyncio.create_task(self._watchdog_loop())

    async def stop(self) -> None:
        """Para o Watchdog graciosamente."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _watchdog_loop(self) -> None:
        while self._running:
            try:
                await self.check_and_recover_stale_documents()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Erro no ciclo do IngestionWatchdog: %s", exc)

            try:
                await asyncio.sleep(self._interval_seconds)
            except asyncio.CancelledError:
                break
