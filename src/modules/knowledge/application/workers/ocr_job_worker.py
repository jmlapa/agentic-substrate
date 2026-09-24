import asyncio
from collections.abc import Awaitable, Callable
from uuid import uuid4

import asyncpg

from src.kernel.infrastructure.atomic_job_barrier import AtomicJobBarrier
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.domain.interfaces.i_stream_job_queue import IStreamJobQueue
from src.modules.knowledge.domain.value_objects.job_task import JobTask
from src.modules.knowledge.domain.value_objects.page_ocr_job_payload import PageOcrJobPayload
from src.modules.knowledge.infrastructure.adapters.page_checkpoint_storage import (
    PageCheckpointStorage,
)


class OcrJobWorker:
    """
    Worker autônomo para processamento distribuído de OCR página a página via Redis Streams.
    Consome de 'stream:jobs:ocr', valida checkpoints duráveis para evitar repetições,
    emite heartbeats no PostgreSQL e coordena a junção das páginas via AtomicJobBarrier.
    """

    def __init__(
        self,
        stream_queue: IStreamJobQueue,
        storage: IObjectStorage,
        checkpoint_storage: PageCheckpointStorage,
        barrier: AtomicJobBarrier,
        pool: asyncpg.Pool | None = None,
        page_parser_fn: Callable[[PageOcrJobPayload], Awaitable[str]] | None = None,
        stream_name: str = "stream:jobs:ocr",
        group_name: str = "ocr_workers",
        consumer_name: str | None = None,
        on_completed_callback: Callable[[PageOcrJobPayload, str], Awaitable[None]] | None = None,
    ) -> None:
        self._stream_queue = stream_queue
        self._storage = storage
        self._checkpoint_storage = checkpoint_storage
        self._barrier = barrier
        self._pool = pool
        self._page_parser_fn = page_parser_fn
        self._stream_name = stream_name
        self._group_name = group_name
        self._consumer_name = consumer_name or f"ocr-worker-{uuid4().hex[:8]}"
        self._on_completed = on_completed_callback
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def run_once(self, count: int = 10, block_ms: int = 500) -> int:
        """Consome e processa um lote de tarefas pendentes ou tarefas ociosas (stale)."""
        tasks = await self._stream_queue.consume_tasks(
            stream_name=self._stream_name,
            group_name=self._group_name,
            consumer_name=self._consumer_name,
            count=count,
            block_ms=block_ms,
        )
        if not tasks:
            # Tenta recuperar tarefas de workers que caíram há mais de 60 segundos
            tasks = await self._stream_queue.claim_stale_tasks(
                stream_name=self._stream_name,
                group_name=self._group_name,
                consumer_name=self._consumer_name,
                min_idle_time_ms=60000,
                count=count,
            )

        processed = 0
        for msg_id, task in tasks:
            success = await self.process_task(msg_id, task)
            if success:
                processed += 1
        return processed

    async def process_task(self, msg_id: str, task: JobTask) -> bool:
        """Executa uma única tarefa de OCR com persistência durável e barreira de junção."""
        try:
            payload = PageOcrJobPayload.model_validate(task.payload)

            # 1. Verifica se a página já está no checkpoint de disco ($0.00 em tokens adicionais)
            has_checkpoint = await self._checkpoint_storage.has_page(
                kb_partition=payload.storage_partition,
                doc_id=payload.document_id,
                page_num=payload.page_number,
            )

            if not has_checkpoint:
                if self._page_parser_fn is not None:
                    page_md = await self._page_parser_fn(payload)
                else:
                    page_md = f"<!-- Page {payload.page_number} -->\n"

                await self._checkpoint_storage.save_page(
                    kb_partition=payload.storage_partition,
                    doc_id=payload.document_id,
                    page_num=payload.page_number,
                    content=page_md,
                )

            # 2. Emite heartbeat no PostgreSQL
            await self._emit_heartbeat(payload)

            # 3. Barreira atômica de coordenação
            is_last = await self._barrier.increment_and_check(payload.document_id, step="ocr")
            if is_last:
                await self._consolidate_full_document(payload)

            # 4. Confirma o processamento no Redis Streams
            await self._stream_queue.ack_task(self._stream_name, self._group_name, msg_id)
            return True

        except Exception:
            # Deixa a mensagem na fila/PEL para reatribuição ou tratamento pelo Watchdog
            return False

    async def _emit_heartbeat(self, payload: PageOcrJobPayload) -> None:
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE attached_documents SET updated_at = NOW() WHERE id = $1;",
                payload.document_id,
            )

    async def _consolidate_full_document(self, payload: PageOcrJobPayload) -> None:
        """Consolida todas as páginas do documento em Markdown e avança para a próxima etapa."""
        pages_content: list[str] = []
        for p in range(1, payload.total_pages + 1):
            content = await self._checkpoint_storage.get_page(
                kb_partition=payload.storage_partition,
                doc_id=payload.document_id,
                page_num=p,
            )
            pages_content.append(content or "")

        full_md = "\n\n---\n\n".join(pages_content)
        md_storage_path = f"{payload.storage_partition}/markdown/{payload.document_id}.md"
        await self._storage.put_object(md_storage_path, full_md.encode("utf-8"), "text/markdown")

        if self._pool is not None:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE attached_documents
                    SET status = 'PARSED',
                        progress_step = 'CHUNKING',
                        progress_percentage = 30,
                        updated_at = NOW()
                    WHERE id = $1;
                    """,
                    payload.document_id,
                )

        if self._on_completed is not None:
            await self._on_completed(payload, md_storage_path)

    async def start(self) -> None:
        """Inicia o loop contínuo do worker em background."""
        self._running = True
        self._task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        """Para o worker graciosamente."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                await self.run_once(count=10, block_ms=1000)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1.0)
