import logging
from uuid import UUID

from src.kernel.application.event_bus import EventBus
from src.kernel.application.logger import Logger
from src.kernel.domain.domain_event import DomainEvent
from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.events.data_source_run_completed_event import (
    DataSourceRunCompletedEvent,
)
from src.modules.knowledge.domain.events.document_knowledge_indexed_event import (
    DocumentKnowledgeIndexedEvent,
)
from src.modules.knowledge.domain.events.document_processing_failed_event import (
    DocumentProcessingFailedEvent,
)
from src.modules.knowledge.domain.interfaces.i_data_source_run_repository import (
    IDataSourceRunRepository,
)

_standard_logger = logging.getLogger("agentic_substrate.handlers.data_source_run_projector")


class DataSourceRunProjector:
    """
    Projetor reativo que escuta eventos de conclusão e falha de documentos no pipeline GraphRAG,
    atualizando os contadores de indexed e failed de cada DataSourceRun correspondente.
    Quando todos os documentos do lote forem processados, finaliza a execução.
    """

    def __init__(
        self,
        data_source_run_repository: IDataSourceRunRepository,
        event_bus: EventBus | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._run_repo = data_source_run_repository
        self._event_bus = event_bus
        self._logger = logger

    def _log_info(self, message: str) -> None:
        if self._logger:
            self._logger.info(message)
        else:
            _standard_logger.info(message)

    def _log_error(self, message: str) -> None:
        if self._logger:
            self._logger.error(message)
        else:
            _standard_logger.error(message)

    def _log_debug(self, message: str) -> None:
        if self._logger:
            self._logger.debug(message)
        else:
            _standard_logger.debug(message)

    async def handle(self, event: DomainEvent) -> None:
        if isinstance(event, DocumentKnowledgeIndexedEvent):
            await self._handle_document_indexed(event)
        elif isinstance(event, DocumentProcessingFailedEvent):
            await self._handle_document_failed(event)

    async def _handle_document_indexed(self, event: DocumentKnowledgeIndexedEvent) -> None:
        sync_run_id_val = event.metadata.get("sync_run_id")
        if not sync_run_id_val:
            return

        try:
            run_id = UUID(str(sync_run_id_val))
        except (ValueError, AttributeError):
            return

        run = await self._run_repo.get_by_id(run_id)
        if run is None:
            self._log_debug(f"[DataSourceRunProjector] Run '{run_id}' não encontrada.")
            return

        run.record_document_indexed()
        processed = run.indexed_files_count + run.failed_files_count
        self._log_info(
            f"[DataSourceRunProjector] Doc '{event.document_id}' indexado na run '{run.id}'. "
            f"Progresso: {processed}/{run.total_files_discovered}"
        )

        if run.completed_at is not None and self._event_bus:
            await self._publish_run_completed(run)

        await self._run_repo.save(run)

    async def _handle_document_failed(self, event: DocumentProcessingFailedEvent) -> None:
        sync_run_id_val = event.metadata.get("sync_run_id")
        if not sync_run_id_val:
            return

        try:
            run_id = UUID(str(sync_run_id_val))
        except (ValueError, AttributeError):
            return

        run = await self._run_repo.get_by_id(run_id)
        if run is None:
            self._log_debug(f"[DataSourceRunProjector] Run '{run_id}' não encontrada.")
            return

        file_name = str(event.metadata.get("file_name") or event.document_id)
        run.record_document_failed(
            doc_id=event.document_id,
            file_name=file_name,
            error=event.error_message,
        )
        processed = run.indexed_files_count + run.failed_files_count
        self._log_error(
            f"[DataSourceRunProjector] Doc '{event.document_id}' falhou na run '{run.id}': "
            f"{event.error_message}. Progresso: {processed}/{run.total_files_discovered}"
        )

        if run.completed_at is not None and self._event_bus:
            await self._publish_run_completed(run)

        await self._run_repo.save(run)

    async def _publish_run_completed(self, run: DataSourceRun) -> None:
        if not self._event_bus:
            return
        self._log_info(
            f"[DataSourceRunProjector] Run '{run.id}' finalizada com status '{run.status.value}'. "
            f"(Total={run.total_files_discovered}, Sucesso={run.indexed_files_count}, "
            f"Falhas={run.failed_files_count})"
        )
        await self._event_bus.publish(
            [
                DataSourceRunCompletedEvent(
                    aggregate_id=run.id,
                    aggregate_type="DataSourceRun",
                    run_id=run.id,
                    data_source_id=run.data_source_id,
                    kb_id=run.kb_id,
                    status=run.status.value,
                    total_files=run.total_files_discovered,
                    indexed_files=run.indexed_files_count,
                    failed_files=run.failed_files_count,
                )
            ]
        )
