from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentResponse,
    AttachAndStoreDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.reprocess_document import (
    ReprocessDocumentResponse,
    ReprocessDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.retry_failed_data_source_items import (
    RetryFailedDataSourceItemsRequest,
    RetryFailedDataSourceItemsUseCase,
)
from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.value_objects.data_source_run_status import (
    DataSourceRunStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_status import (
    DataSourceStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)
from src.modules.knowledge.infrastructure.adapters.data_source_connector_registry import (
    DataSourceConnectorRegistry,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_repository import (
    InMemoryDataSourceRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_run_repository import (
    InMemoryDataSourceRunRepository,
)


@pytest.mark.asyncio
async def test_retry_failed_items_dual_routing_and_cursor_promotion() -> None:
    kb_id = uuid4()
    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()

    data_source = DataSource(
        kb_id=kb_id,
        name="Team Drive",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        cursor="token-old",
        config={"folder_id": "f-123"},
    )
    # Define pending_cursor simulando falha anterior
    data_source.set_pending_cursor("token-new-promoted")
    await ds_repo.save(data_source)

    run = DataSourceRun(
        data_source_id=data_source.id,
        kb_id=kb_id,
        status=DataSourceRunStatus.PARTIALLY_FAILED,
        total_files_discovered=2,
    )
    existing_doc_id = uuid4()
    # Item 1: falha pós-attach (tem doc_id)
    run.record_document_failed(
        doc_id=existing_doc_id,
        file_name="doc_ingest_failed.docx",
        error="LLM extraction error",
        external_id="ext-doc-1",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    # Item 2: falha no download (doc_id is None)
    run.record_document_failed(
        doc_id=None,
        file_name="doc_download_failed.docx",
        error="[SSL] record layer failure",
        external_id="ext-doc-2",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    await run_repo.save(run)

    mock_connector = MagicMock()
    mock_connector.download_document = AsyncMock(
        return_value=(b"Binary content of doc 2", "text/plain", "hash-222")
    )
    registry = DataSourceConnectorRegistry()
    registry.register(DataSourceType.GOOGLE_DRIVE_FOLDER, mock_connector)

    attach_use_case = MagicMock(spec=AttachAndStoreDocumentUseCase)
    attach_use_case.execute = AsyncMock(
        return_value=Ok(
            AttachAndStoreDocumentResponse(
                document_id=uuid4(),
                storage_path="/tmp/doc_download_failed.docx",
                status="UPLOADED",
            )
        )
    )

    reprocess_use_case = MagicMock(spec=ReprocessDocumentUseCase)
    reprocess_use_case.execute = AsyncMock(
        return_value=Ok(
            ReprocessDocumentResponse(
                document_id=existing_doc_id,
                status="COMPLETED",
                message="Retomado com sucesso a partir de CHUNKED",
            )
        )
    )

    use_case = RetryFailedDataSourceItemsUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=registry,
        attach_use_case=attach_use_case,
        reprocess_document_use_case=reprocess_use_case,
    )

    req = RetryFailedDataSourceItemsRequest(
        kb_id=kb_id, data_source_id=data_source.id, run_id=run.id
    )
    result = await use_case.execute(req)

    assert isinstance(result, Ok)
    assert result.value.reprocessed_count == 2
    assert result.value.remaining_failed_count == 0
    assert result.value.status == "COMPLETED"

    # Verifica roteamento:
    # 1. doc_ingest_failed foi chamado via reprocess_document_use_case
    reprocess_use_case.execute.assert_called_once()
    assert reprocess_use_case.execute.call_args[0][0].document_id == existing_doc_id

    # 2. doc_download_failed foi baixado via conector e anexado
    mock_connector.download_document.assert_called_once_with(
        "ext-doc-2", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    attach_use_case.execute.assert_called_once()

    # 3. Cursor foi promovido com sucesso para token-new-promoted
    updated_ds = await ds_repo.get_by_id(data_source.id)
    assert updated_ds is not None
    assert updated_ds.cursor == "token-new-promoted"
    assert updated_ds.pending_cursor is None
    assert updated_ds.status == DataSourceStatus.IDLE


@pytest.mark.asyncio
async def test_retry_failed_items_concurrency_conflict() -> None:
    kb_id = uuid4()
    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()

    data_source = DataSource(
        kb_id=kb_id,
        name="Team Drive",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        status=DataSourceStatus.SYNCING,  # Já em sincronização
    )
    await ds_repo.save(data_source)

    run = DataSourceRun(data_source_id=data_source.id, kb_id=kb_id)
    await run_repo.save(run)

    use_case = RetryFailedDataSourceItemsUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=MagicMock(),
        attach_use_case=MagicMock(),
        reprocess_document_use_case=MagicMock(),
    )

    req = RetryFailedDataSourceItemsRequest(
        kb_id=kb_id, data_source_id=data_source.id, run_id=run.id
    )
    result = await use_case.execute(req)

    assert isinstance(result, Err)
    assert result.error.code == "CONCURRENCY_CONFLICT"
