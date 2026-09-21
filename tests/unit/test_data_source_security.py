from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentResponse,
    AttachAndStoreDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.sync_data_source import (
    SyncDataSourceRequest,
    SyncDataSourceUseCase,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.value_objects.data_source_changes_batch import (
    DataSourceChangesBatch,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)
from src.modules.knowledge.domain.value_objects.discovered_document_item import (
    DiscoveredDocumentItem,
)
from src.modules.knowledge.domain.value_objects.google_drive_folder_config import (
    GoogleDriveFolderConfig,
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
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)


def test_google_drive_folder_config_rejects_query_injection_in_folder_id() -> None:
    # Valid folder IDs
    cfg_root = GoogleDriveFolderConfig(folder_id="root")
    assert cfg_root.folder_id == "root"

    cfg_alphanumeric = GoogleDriveFolderConfig(folder_id="1aBcDeFg_Hi-JkLmNo0123")
    assert cfg_alphanumeric.folder_id == "1aBcDeFg_Hi-JkLmNo0123"

    # Malicious injection attempts with single quotes, operators, or whitespace
    malicious_inputs = [
        "root' or trashed = false",
        "123' or 'a'='a",
        "folder; DROP TABLE users;",
        "folder/../other",
        "folder with spaces",
        "folder'--",
    ]
    for bad_id in malicious_inputs:
        with pytest.raises(ValidationError, match="folder_id contains invalid characters"):
            GoogleDriveFolderConfig(folder_id=bad_id)


def test_google_drive_folder_config_forbids_extra_fields() -> None:
    # Extra fields (such as accidentally leaked secrets or tokens) must be forbidden
    with pytest.raises(ValidationError):
        GoogleDriveFolderConfig(
            folder_id="valid_folder_123",
            service_account_private_key="leaked_key_here",  # type: ignore[call-arg]
        )


@pytest.mark.asyncio
async def test_sync_data_source_sanitizes_path_traversal_in_file_names() -> None:
    kb_id = uuid4()
    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()
    kb_repo = InMemoryKnowledgeBaseRepository()
    registry = DataSourceConnectorRegistry()
    event_bus = AsyncMock()

    # Pre-populate KnowledgeBase
    kb = KnowledgeBaseAggregate(id=kb_id)
    await kb_repo.save(kb)

    # Setup DataSource
    ds = DataSource(
        kb_id=kb_id,
        name="Drive Source",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "test_folder"},
    )
    await ds_repo.save(ds)

    # Mock connector returning a file with a path traversal name
    mock_connector = AsyncMock()
    mock_connector.fetch_changes.return_value = DataSourceChangesBatch(
        items=[
            DiscoveredDocumentItem(
                external_id="ext-traversal-01",
                name="../../etc/passwd",
                mime_type="text/plain",
                version_hash="hash_traversal",
                size_bytes=100,
                modified_time=datetime.now(UTC),
            )
        ],
        next_cursor="c1",
        deleted_external_ids=[],
    )
    mock_connector.download_document.return_value = (b"root:x:0:0", "text/plain", "hash_traversal")
    registry.register(DataSourceType.GOOGLE_DRIVE_FOLDER, mock_connector)

    # Mock attach use case
    mock_attach = AsyncMock(spec=AttachAndStoreDocumentUseCase)
    from src.kernel.domain.result import Ok

    mock_attach.execute.return_value = Ok(
        AttachAndStoreDocumentResponse(
            document_id=uuid4(),
            storage_path="kb/raw/safe.txt",
            status="UPLOADED",
        )
    )

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        kb_repository=kb_repo,
        connector_registry=registry,
        attach_use_case=mock_attach,
        event_bus=event_bus,
    )

    result = await use_case.execute(SyncDataSourceRequest(data_source_id=ds.id))
    assert isinstance(result, Ok)

    # Verify that the file name passed to attach use case was sanitized to basename
    mock_attach.execute.assert_called_once()
    called_request = mock_attach.execute.call_args[0][0]
    assert called_request.file_name == "passwd"
    assert "/" not in called_request.file_name
    assert ".." not in called_request.file_name


@pytest.mark.asyncio
async def test_sync_data_source_rejects_oversized_files_before_download() -> None:
    kb_id = uuid4()
    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()
    kb_repo = InMemoryKnowledgeBaseRepository()
    registry = DataSourceConnectorRegistry()
    event_bus = AsyncMock()

    kb = KnowledgeBaseAggregate(id=kb_id)
    await kb_repo.save(kb)

    ds = DataSource(
        kb_id=kb_id,
        name="Drive Source",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "test_folder"},
    )
    await ds_repo.save(ds)

    # 100 MB file, exceeding the 50 MB safety limit
    huge_file_size = 100 * 1024 * 1024
    mock_connector = AsyncMock()
    mock_connector.fetch_changes.return_value = DataSourceChangesBatch(
        items=[
            DiscoveredDocumentItem(
                external_id="ext-huge-01",
                name="huge_dump.iso",
                mime_type="application/octet-stream",
                version_hash="hash_huge",
                size_bytes=huge_file_size,
                modified_time=datetime.now(UTC),
            )
        ],
        next_cursor="c1",
        deleted_external_ids=[],
    )
    registry.register(DataSourceType.GOOGLE_DRIVE_FOLDER, mock_connector)

    mock_attach = AsyncMock(spec=AttachAndStoreDocumentUseCase)

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        kb_repository=kb_repo,
        connector_registry=registry,
        attach_use_case=mock_attach,
        event_bus=event_bus,
        max_file_size_bytes=50 * 1024 * 1024,
    )

    from src.kernel.domain.result import Ok

    result = await use_case.execute(SyncDataSourceRequest(data_source_id=ds.id))
    assert isinstance(result, Ok)

    # download_document should NEVER be called for the oversized file
    mock_connector.download_document.assert_not_called()
    mock_attach.execute.assert_not_called()

    # The run must record the failure due to file size
    run = await run_repo.get_by_id(result.value.sync_run_id)
    assert run is not None
    assert run.failed_files_count == 1
    assert any("exceeds maximum allowed size" in f.get("error", "") for f in run.failure_summary)
