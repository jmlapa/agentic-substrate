import logging
from typing import Any
from uuid import UUID

from src.kernel.application.logger import Logger
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentRequest,
    AttachAndStoreDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.reprocess_document import (
    ReprocessDocumentRequest,
    ReprocessDocumentUseCase,
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
from src.modules.knowledge.domain.value_objects.data_source_status import (
    DataSourceStatus,
)

from .retry_failed_data_source_items_request import (
    RetryFailedDataSourceItemsRequest,
)
from .retry_failed_data_source_items_response import (
    RetryFailedDataSourceItemsResponse,
)

_standard_logger = logging.getLogger("agentic_substrate.use_cases.retry_failed_items")


class RetryFailedDataSourceItemsUseCase:
    """Caso de uso para reprocessamento manual dos itens que falharam em um DataSourceRun.

    Aplica roteamento dual:
    - Se doc_id is None: re-baixa do conector externo e executa attach_and_store.
    - Se doc_id is not None: retoma o documento existente via ReprocessDocumentUseCase.
    Garante bloqueio de concorrência com status SYNCING e promove o pending_cursor caso
    todas as falhas sejam sanadas.
    """

    def __init__(
        self,
        data_source_repository: IDataSourceRepository,
        data_source_run_repository: IDataSourceRunRepository,
        connector_registry: IDataSourceConnectorRegistry,
        attach_use_case: AttachAndStoreDocumentUseCase,
        reprocess_document_use_case: ReprocessDocumentUseCase,
        logger: Logger | None = None,
    ) -> None:
        self._ds_repo = data_source_repository
        self._run_repo = data_source_run_repository
        self._registry = connector_registry
        self._attach_use_case = attach_use_case
        self._reprocess_doc_use_case = reprocess_document_use_case
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

    async def execute(
        self, request: RetryFailedDataSourceItemsRequest
    ) -> Result[RetryFailedDataSourceItemsResponse, DomainError]:
        data_source = await self._ds_repo.get_by_id(request.data_source_id)
        if data_source is None or data_source.kb_id != request.kb_id:
            return Err(
                DomainError(
                    f"DataSource '{request.data_source_id}' não encontrado na KB '{request.kb_id}'",
                    code="NOT_FOUND",
                )
            )

        if data_source.status == DataSourceStatus.SYNCING:
            return Err(
                DomainError(
                    f"DataSource '{data_source.id}' já está em sincronização ou reprocessamento.",
                    code="CONCURRENCY_CONFLICT",
                )
            )

        run = await self._run_repo.get_by_id(request.run_id)
        if run is None or run.data_source_id != data_source.id:
            return Err(
                DomainError(
                    f"DataSourceRun '{request.run_id}' não encontrado para "
                    f"DataSource '{data_source.id}'",
                    code="NOT_FOUND",
                )
            )

        if not run.failure_summary:
            return Ok(
                RetryFailedDataSourceItemsResponse(
                    data_source_id=data_source.id,
                    run_id=run.id,
                    reprocessed_count=0,
                    remaining_failed_count=0,
                    status=run.status.value,
                )
            )

        # Bloqueia o status do data_source contra concorrência
        data_source.start_sync()
        await self._ds_repo.save(data_source)

        run.mark_retrying()
        await self._run_repo.save(run)

        reprocessed_count = 0
        try:
            connector = self._registry.get_connector(data_source.data_source_type)

            for fail in list(run.failure_summary):
                file_name = str(fail.get("file_name", ""))
                doc_id_str = fail.get("doc_id")

                if doc_id_str:
                    # Falha após attach: reprocessa documento já salvo no Object Storage
                    self._log_info(f"[RetryFailedItems] Reprocessando doc_id='{doc_id_str}'...")
                    reproc_res = await self._reprocess_doc_use_case.execute(
                        ReprocessDocumentRequest(kb_id=request.kb_id, document_id=UUID(doc_id_str))
                    )
                    if isinstance(reproc_res, Ok):
                        run.resolve_item_success(file_name)
                        reprocessed_count += 1
                    else:
                        self._log_error(
                            f"[RetryFailedItems] Falha ao reprocessar doc_id='{doc_id_str}': "
                            f"{reproc_res.error.message}"
                        )
                else:
                    # Falha no download ou attach: re-baixa do conector externo
                    ext_id = fail.get("external_id")
                    mime_type = fail.get("mime_type", "application/octet-stream")
                    if not ext_id:
                        self._log_error(
                            f"[RetryFailedItems] Item '{file_name}' não possui external_id na DLQ."
                        )
                        continue

                    try:
                        self._log_info(
                            f"[RetryFailedItems] Re-baixando '{file_name}' (ext_id='{ext_id}')..."
                        )
                        content, resolved_mime, version_hash = await connector.download_document(
                            ext_id, mime_type
                        )

                        source_metadata: dict[str, Any] = {
                            "data_source_id": str(data_source.id),
                            "sync_run_id": str(run.id),
                            "external_id": ext_id,
                            "version_hash": version_hash,
                        }

                        attach_req = AttachAndStoreDocumentRequest(
                            kb_id=request.kb_id,
                            file_name=file_name,
                            content_type=resolved_mime,
                            file_content=content,
                            source_metadata=source_metadata,
                        )
                        attach_res = await self._attach_use_case.execute(attach_req)
                        if isinstance(attach_res, Ok):
                            run.resolve_item_success(file_name)
                            reprocessed_count += 1
                        else:
                            self._log_error(
                                f"[RetryFailedItems] Falha ao anexar '{file_name}': "
                                f"{attach_res.error.message}"
                            )
                    except Exception as err:
                        self._log_error(
                            f"[RetryFailedItems] Exceção ao re-baixar '{file_name}': {err}"
                        )

            # Se todas as falhas foram sanadas, promove o cursor pendente
            if run.failed_files_count == 0:
                self._log_info(
                    f"[RetryFailedItems] Todas as falhas foram recuperadas. "
                    f"Promovendo pending_cursor '{data_source.pending_cursor}' para cursor ativo."
                )
                data_source.promote_pending_cursor()

            data_source.complete_sync(new_cursor=None)
            await self._ds_repo.save(data_source)
            await self._run_repo.save(run)

            return Ok(
                RetryFailedDataSourceItemsResponse(
                    data_source_id=data_source.id,
                    run_id=run.id,
                    reprocessed_count=reprocessed_count,
                    remaining_failed_count=run.failed_files_count,
                    status=run.status.value,
                )
            )

        except Exception as e:
            err_msg = str(e)
            self._log_error(f"[RetryFailedItems] Erro inesperado no reprocessamento: {err_msg}")
            data_source.fail_sync(err_msg)
            await self._ds_repo.save(data_source)
            return Err(DomainError(err_msg, code="INTERNAL_ERROR"))
