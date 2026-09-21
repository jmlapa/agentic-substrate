import asyncio
import logging
from typing import Any
from uuid import UUID

from src.kernel.application.event_bus import EventBus
from src.kernel.application.logger import Logger
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentRequest,
    AttachAndStoreDocumentUseCase,
)
from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.events.data_source_sync_completed_event import (
    DataSourceSyncCompletedEvent,
)
from src.modules.knowledge.domain.events.data_source_sync_failed_event import (
    DataSourceSyncFailedEvent,
)
from src.modules.knowledge.domain.events.data_source_sync_started_event import (
    DataSourceSyncStartedEvent,
)
from src.modules.knowledge.domain.interfaces.i_data_source_connector_registry import (
    IDataSourceConnectorRegistry,
)
from src.modules.knowledge.domain.interfaces.i_data_source_repository import (
    IDataSourceRepository,
)
from src.modules.knowledge.domain.interfaces.i_data_source_run_repository import (
    IDataSourceRunRepository,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.value_objects.data_source_run_status import (
    DataSourceRunStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_status import (
    DataSourceStatus,
)
from src.modules.knowledge.domain.value_objects.discovered_document_item import (
    DiscoveredDocumentItem,
)

from .sync_data_source_request import SyncDataSourceRequest
from .sync_data_source_response import SyncDataSourceResponse

_standard_logger = logging.getLogger("agentic_substrate.use_cases.sync_data_source")


class SyncDataSourceUseCase:
    def __init__(
        self,
        data_source_repository: IDataSourceRepository,
        data_source_run_repository: IDataSourceRunRepository,
        connector_registry: IDataSourceConnectorRegistry,
        kb_repository: IKnowledgeBaseRepository,
        attach_use_case: AttachAndStoreDocumentUseCase,
        event_bus: EventBus | None = None,
        logger: Logger | None = None,
        max_concurrency: int = 2,
    ) -> None:
        self._ds_repo = data_source_repository
        self._run_repo = data_source_run_repository
        self._registry = connector_registry
        self._kb_repo = kb_repository
        self._attach_use_case = attach_use_case
        self._event_bus = event_bus
        self._logger = logger
        self._max_concurrency = max(1, max_concurrency)

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

    async def execute(
        self, request: SyncDataSourceRequest
    ) -> Result[SyncDataSourceResponse, DomainError]:
        self._log_info(
            f"[SyncDataSourceUseCase] Iniciando sync para DataSource id='{request.data_source_id}'"
        )

        data_source = await self._ds_repo.get_by_id(request.data_source_id)
        if data_source is None:
            msg = f"DataSource '{request.data_source_id}' não encontrado."
            self._log_error(f"[SyncDataSourceUseCase] {msg}")
            return Err(DomainError(msg, "DATA_SOURCE_NOT_FOUND"))

        if data_source.status == DataSourceStatus.DISABLED:
            msg = f"DataSource '{data_source.id}' está desativado."
            self._log_error(f"[SyncDataSourceUseCase] {msg}")
            return Err(DomainError(msg, "DATA_SOURCE_DISABLED"))

        if data_source.status == DataSourceStatus.SYNCING:
            msg = f"DataSource '{data_source.id}' já está em sincronização."
            self._log_error(f"[SyncDataSourceUseCase] {msg}")
            return Err(DomainError(msg, "DATA_SOURCE_ALREADY_SYNCING"))

        data_source.start_sync()
        await self._ds_repo.save(data_source)

        run = DataSourceRun(
            data_source_id=data_source.id,
            kb_id=data_source.kb_id,
            status=DataSourceRunStatus.EXTRACTING,
        )
        await self._run_repo.save(run)

        if self._event_bus:
            await self._event_bus.publish(
                [
                    DataSourceSyncStartedEvent(
                        aggregate_id=data_source.id,
                        aggregate_type="DataSource",
                        data_source_id=data_source.id,
                        run_id=run.id,
                        kb_id=data_source.kb_id,
                    )
                ]
            )

        try:
            connector = self._registry.get_connector(data_source.data_source_type)
            self._log_info(
                f"[SyncDataSourceUseCase] Consultando conector para DataSource '{data_source.id}' "
                f"(tipo={data_source.data_source_type.value}, cursor={data_source.cursor})"
            )
            changes = await connector.fetch_changes(data_source.config, data_source.cursor)
            self._log_info(
                f"[SyncDataSourceUseCase] Descobertos {len(changes.items)} arquivos e "
                f"{len(changes.deleted_external_ids)} exclusões. "
                f"Próximo cursor='{changes.next_cursor}'"
            )

            run.mark_ingesting(len(changes.items))
            await self._run_repo.save(run)

            kb = await self._kb_repo.get_by_id(data_source.kb_id)
            existing_docs_by_name: dict[str, UUID] = {}
            if kb:
                for doc_id, doc_info in kb.documents.items():
                    name = doc_info.get("file_name")
                    if name:
                        existing_docs_by_name[name] = doc_id

            semaphore = asyncio.Semaphore(self._max_concurrency)

            async def _process_item(item: DiscoveredDocumentItem) -> None:
                async with semaphore:
                    content: bytes | None = None
                    try:
                        self._log_info(
                            f"[SyncDataSourceUseCase] Baixando item '{item.name}' "
                            f"(id={item.external_id})..."
                        )
                        content, resolved_mime, version_hash = await connector.download_document(
                            item.external_id, item.mime_type
                        )

                        replaces_doc_id = existing_docs_by_name.get(item.name)
                        source_metadata: dict[str, Any] = {
                            "data_source_id": str(data_source.id),
                            "sync_run_id": str(run.id),
                            "external_id": item.external_id,
                            "version_hash": version_hash,
                            "replaces_doc_id": str(replaces_doc_id) if replaces_doc_id else None,
                        }

                        self._log_info(
                            f"[SyncDataSourceUseCase] Enviando '{item.name}' para attach "
                            f"(replaces_doc_id={replaces_doc_id}, run_id={run.id})..."
                        )

                        attach_req = AttachAndStoreDocumentRequest(
                            kb_id=data_source.kb_id,
                            file_name=item.name,
                            content_type=resolved_mime,
                            file_content=content,
                            source_metadata=source_metadata,
                        )
                        attach_res = await self._attach_use_case.execute(attach_req)
                        if isinstance(attach_res, Err):
                            err_msg = f"Falha no attach_document: {attach_res.error.message}"
                            self._log_error(
                                f"[SyncDataSourceUseCase] Erro no item '{item.name}': {err_msg}"
                            )
                            run.record_document_failed(
                                doc_id=None, file_name=item.name, error=err_msg
                            )
                        else:
                            self._log_info(
                                f"[SyncDataSourceUseCase] Item '{item.name}' anexado: "
                                f"doc_id='{attach_res.value.document_id}'"
                            )
                    except Exception as item_err:
                        err_msg = str(item_err)
                        self._log_error(
                            f"[SyncDataSourceUseCase] Falha ao processar item '{item.name}': "
                            f"{err_msg}"
                        )
                        run.record_document_failed(doc_id=None, file_name=item.name, error=err_msg)
                    finally:
                        content = None

            if changes.items:
                await asyncio.gather(*[_process_item(item) for item in changes.items])

            latest_run = await self._run_repo.get_by_id(run.id)
            if latest_run is not None:
                run = latest_run

            data_source.complete_sync(new_cursor=changes.next_cursor)
            await self._ds_repo.save(data_source)

            if self._event_bus:
                await self._event_bus.publish(
                    [
                        DataSourceSyncCompletedEvent(
                            aggregate_id=data_source.id,
                            aggregate_type="DataSource",
                            data_source_id=data_source.id,
                            run_id=run.id,
                            synced_files_count=len(changes.items),
                            new_cursor=changes.next_cursor,
                        )
                    ]
                )

            self._log_info(
                f"[SyncDataSourceUseCase] Sincronização concluída com sucesso para DataSource "
                f"'{data_source.id}' (run_id={run.id}, status={run.status.value})"
            )

            return Ok(
                SyncDataSourceResponse(
                    data_source_id=data_source.id,
                    sync_run_id=run.id,
                    total_items_discovered=len(changes.items),
                    status=run.status.value,
                )
            )

        except Exception as e:
            err_str = str(e)
            self._log_error(
                f"[SyncDataSourceUseCase] Erro crítico na sincronização do DataSource "
                f"'{data_source.id}': {err_str}"
            )
            data_source.fail_sync(err_str)
            await self._ds_repo.save(data_source)

            if self._event_bus:
                await self._event_bus.publish(
                    [
                        DataSourceSyncFailedEvent(
                            aggregate_id=data_source.id,
                            aggregate_type="DataSource",
                            data_source_id=data_source.id,
                            run_id=run.id,
                            error_message=err_str,
                        )
                    ]
                )

            return Err(DomainError(err_str, "DATA_SOURCE_SYNC_FAILED"))
