import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.domain.result import Ok
from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentResponse,
    AttachAndStoreDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.sync_data_source import (
    SyncDataSourceRequest,
    SyncDataSourceUseCase,
)
from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.value_objects.data_source_changes_batch import (
    DataSourceChangesBatch,
)
from src.modules.knowledge.domain.value_objects.data_source_run_status import (
    DataSourceRunStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)
from src.modules.knowledge.domain.value_objects.discovered_document_item import (
    DiscoveredDocumentItem,
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
async def test_idempotency_gate_skips_already_indexed_identical_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    kb_id = uuid4()
    existing_doc_id = uuid4()

    # KB já possui o arquivo ext-1 indexado com o hash 'sha256-abc'
    kb_mock = MagicMock()
    kb_mock.documents = {
        existing_doc_id: {
            "id": existing_doc_id,
            "file_name": "daily_2026_09_08.docx",
            "status": "INDEXED",
            "metadata": {
                "external_id": "ext-1",
                "version_hash": "sha256-abc",
            },
        }
    }
    kb_repo = MagicMock()
    kb_repo.get_by_id = AsyncMock(return_value=kb_mock)

    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()

    data_source = DataSource(
        kb_id=kb_id,
        name="Dailies Drive",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "folder-123"},
    )
    await ds_repo.save(data_source)

    now = datetime.now(UTC)
    # Conector retorna o arquivo ext-1 com o mesmo hash e um novo arquivo ext-2
    mock_connector = MagicMock()
    mock_connector.fetch_changes = AsyncMock(
        return_value=DataSourceChangesBatch(
            items=[
                DiscoveredDocumentItem(
                    external_id="ext-1",
                    name="daily_2026_09_08.docx",
                    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    version_hash="sha256-abc",
                    modified_time=now,
                ),
                DiscoveredDocumentItem(
                    external_id="ext-2",
                    name="daily_2026_09_09.docx",
                    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    version_hash="sha256-xyz",
                    modified_time=now,
                ),
            ],
            next_cursor="token-final-99",
            deleted_external_ids=[],
        )
    )
    mock_connector.download_document = AsyncMock(
        return_value=(b"Content of doc 2", "text/plain", "sha256-xyz")
    )

    registry = DataSourceConnectorRegistry()
    registry.register(DataSourceType.GOOGLE_DRIVE_FOLDER, mock_connector)

    attach_use_case = MagicMock(spec=AttachAndStoreDocumentUseCase)
    attach_use_case.execute = AsyncMock(
        return_value=Ok(
            AttachAndStoreDocumentResponse(
                document_id=uuid4(),
                storage_path="/tmp/daily_2026_09_09.docx",
                status="UPLOADED",
            )
        )
    )

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=registry,
        kb_repository=kb_repo,
        attach_use_case=attach_use_case,
    )

    response = await use_case.execute(
        SyncDataSourceRequest(kb_id=kb_id, data_source_id=data_source.id)
    )

    assert isinstance(response, Ok)
    # Verifica que download_document foi chamado apenas para ext-2, e NÃO para ext-1!
    assert mock_connector.download_document.call_count == 1
    mock_connector.download_document.assert_called_once_with(
        "ext-2", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    # Item 1 foi contabilizado imediatamente como indexado (pelo idempotency skip);
    # Item 2 está anexado e em processamento de ingestão
    latest_run = await run_repo.get_by_id(response.value.sync_run_id)
    assert latest_run is not None
    assert latest_run.status == DataSourceRunStatus.INGESTING
    assert latest_run.indexed_files_count == 1
    assert latest_run.failed_files_count == 0


@pytest.mark.asyncio
async def test_safe_cursor_and_dlq_enrichment_on_download_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    kb_id = uuid4()
    kb_mock = MagicMock()
    kb_mock.documents = {}
    kb_repo = MagicMock()
    kb_repo.get_by_id = AsyncMock(return_value=kb_mock)

    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()

    data_source = DataSource(
        kb_id=kb_id,
        name="Dailies Drive",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        cursor="initial-token-10",
        config={"folder_id": "folder-123"},
    )
    await ds_repo.save(data_source)

    now = datetime.now(UTC)
    mock_connector = MagicMock()
    mock_connector.fetch_changes = AsyncMock(
        return_value=DataSourceChangesBatch(
            items=[
                DiscoveredDocumentItem(
                    external_id="ext-fail",
                    name="failed_file.docx",
                    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    version_hash="sha-fail",
                    size_bytes=2048,
                    modified_time=now,
                ),
            ],
            next_cursor="token-after-failure-52",
            deleted_external_ids=[],
        )
    )
    # Sempre falha no download
    mock_connector.download_document = AsyncMock(
        side_effect=RuntimeError("[SSL] record layer failure (_ssl.c:2580)")
    )

    registry = DataSourceConnectorRegistry()
    registry.register(DataSourceType.GOOGLE_DRIVE_FOLDER, mock_connector)

    attach_use_case = MagicMock(spec=AttachAndStoreDocumentUseCase)

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=registry,
        kb_repository=kb_repo,
        attach_use_case=attach_use_case,
    )

    response = await use_case.execute(
        SyncDataSourceRequest(kb_id=kb_id, data_source_id=data_source.id)
    )

    assert isinstance(response, Ok)
    # Verifica que o conector tentou 3 retries antes de desistir
    assert mock_connector.download_document.call_count == 3

    # Verifica entidade DataSource: cursor inicial NÃO avançou para 52!
    updated_ds = await ds_repo.get_by_id(data_source.id)
    assert updated_ds is not None
    assert updated_ds.cursor == "initial-token-10"
    assert updated_ds.pending_cursor == "token-after-failure-52"

    # Verifica DataSourceRun: status FAILED com DLQ enriquecida
    latest_run = await run_repo.get_by_id(response.value.sync_run_id)
    assert latest_run is not None
    assert latest_run.status == DataSourceRunStatus.FAILED
    assert latest_run.failed_files_count == 1
    assert len(latest_run.failure_summary) == 1
    fail_entry = latest_run.failure_summary[0]
    assert fail_entry["file_name"] == "failed_file.docx"
    assert fail_entry["external_id"] == "ext-fail"
    assert fail_entry["mime_type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert fail_entry["version_hash"] == "sha-fail"
    assert fail_entry["size_bytes"] == 2048
    assert "[SSL] record layer failure" in fail_entry["error"]
