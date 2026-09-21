from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.domain_event import DomainEvent
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentRequest,
    AttachAndStoreDocumentResponse,
    AttachAndStoreDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.sync_data_source import (
    SyncDataSourceRequest,
    SyncDataSourceUseCase,
)
from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.events.data_source_sync_completed_event import (
    DataSourceSyncCompletedEvent,
)
from src.modules.knowledge.domain.events.data_source_sync_started_event import (
    DataSourceSyncStartedEvent,
)
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
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_connector import (
    InMemoryDataSourceConnector,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_repository import (
    InMemoryDataSourceRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_run_repository import (
    InMemoryDataSourceRunRepository,
)


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    async def publish(self, events: list[DomainEvent]) -> None:
        self.published.extend(events)

    def subscribe(self, event_type: Any, handler: Any) -> None:
        pass


@pytest.mark.asyncio
async def test_sync_data_source_success_with_multiple_files_and_swap_detection() -> None:
    kb_id = uuid4()
    existing_doc_id = uuid4()

    # Fake KB with one existing document
    kb_mock = MagicMock()
    kb_mock.documents = {
        existing_doc_id: {
            "id": existing_doc_id,
            "file_name": "existing_policy.pdf",
            "content_type": "application/pdf",
        }
    }
    kb_repo = MagicMock()
    kb_repo.get_by_id = AsyncMock(return_value=kb_mock)

    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()
    event_bus = DummyEventBus()

    data_source = DataSource(
        kb_id=kb_id,
        name="Company Drive",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "drive-folder-123"},
    )
    await ds_repo.save(data_source)

    connector = InMemoryDataSourceConnector()
    # Add 5 files: 4 new and 1 existing
    connector.add_mock_file(
        external_id="ext-1",
        name="doc1.txt",
        content=b"Doc 1 text",
        mime_type="text/plain",
    )
    connector.add_mock_file(
        external_id="ext-2",
        name="doc2.txt",
        content=b"Doc 2 text",
        mime_type="text/plain",
    )
    connector.add_mock_file(
        external_id="ext-3",
        name="doc3.pdf",
        content=b"Doc 3 pdf",
        mime_type="application/pdf",
    )
    connector.add_mock_file(
        external_id="ext-4",
        name="doc4.md",
        content=b"Doc 4 markdown",
        mime_type="text/markdown",
    )
    connector.add_mock_file(
        external_id="ext-5",
        name="existing_policy.pdf",  # Same name as existing document!
        content=b"Updated policy v2",
        mime_type="application/pdf",
    )

    registry = DataSourceConnectorRegistry()
    registry.register(DataSourceType.GOOGLE_DRIVE_FOLDER, connector)

    attached_requests: list[AttachAndStoreDocumentRequest] = []

    attach_use_case = MagicMock(spec=AttachAndStoreDocumentUseCase)

    async def fake_attach(
        req: AttachAndStoreDocumentRequest,
    ) -> Ok[AttachAndStoreDocumentResponse]:
        attached_requests.append(req)
        return Ok(
            AttachAndStoreDocumentResponse(
                document_id=uuid4(),
                storage_path=f"path/{req.file_name}",
                status="UPLOADED",
            )
        )

    attach_use_case.execute = AsyncMock(side_effect=fake_attach)

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=registry,
        kb_repository=kb_repo,
        attach_use_case=attach_use_case,
        event_bus=event_bus,
        max_concurrency=2,
    )

    result = await use_case.execute(SyncDataSourceRequest(data_source_id=data_source.id))
    assert isinstance(result, Ok)
    res = result.value
    assert res.data_source_id == data_source.id
    assert res.total_items_discovered == 5
    assert res.status == DataSourceRunStatus.INGESTING.value

    # Check DataSource updated
    updated_ds = await ds_repo.get_by_id(data_source.id)
    assert updated_ds is not None
    assert updated_ds.status == DataSourceStatus.IDLE
    assert updated_ds.cursor == "cursor-token-5"
    assert updated_ds.last_synced_at is not None

    # Check DataSourceRun
    saved_run = await run_repo.get_by_id(res.sync_run_id)
    assert saved_run is not None
    assert saved_run.status == DataSourceRunStatus.INGESTING
    assert saved_run.total_files_discovered == 5
    assert saved_run.failed_files_count == 0

    # Check attach calls and metadata
    assert len(attached_requests) == 5
    swap_requests = [
        r
        for r in attached_requests
        if r.source_metadata.get("replaces_doc_id") == str(existing_doc_id)
    ]
    assert len(swap_requests) == 1
    assert swap_requests[0].file_name == "existing_policy.pdf"

    # Check events published
    assert len(event_bus.published) == 2
    assert isinstance(event_bus.published[0], DataSourceSyncStartedEvent)
    assert isinstance(event_bus.published[1], DataSourceSyncCompletedEvent)


@pytest.mark.asyncio
async def test_sync_data_source_empty_folder() -> None:
    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()
    event_bus = DummyEventBus()

    data_source = DataSource(
        kb_id=uuid4(),
        name="Empty Drive",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "empty-123"},
    )
    await ds_repo.save(data_source)

    connector = InMemoryDataSourceConnector()  # No mock files
    registry = DataSourceConnectorRegistry()
    registry.register(DataSourceType.GOOGLE_DRIVE_FOLDER, connector)

    kb_repo = MagicMock()
    kb_repo.get_by_id = AsyncMock(return_value=MagicMock(documents={}))

    attach_use_case = MagicMock(spec=AttachAndStoreDocumentUseCase)

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=registry,
        kb_repository=kb_repo,
        attach_use_case=attach_use_case,
        event_bus=event_bus,
    )

    result = await use_case.execute(SyncDataSourceRequest(data_source_id=data_source.id))
    assert isinstance(result, Ok)
    assert result.value.total_items_discovered == 0
    assert result.value.status == DataSourceRunStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_sync_data_source_already_syncing() -> None:
    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()

    data_source = DataSource(
        kb_id=uuid4(),
        name="Busy Drive",
        status=DataSourceStatus.SYNCING,
    )
    await ds_repo.save(data_source)

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=MagicMock(),
        kb_repository=MagicMock(),
        attach_use_case=MagicMock(),
    )

    result = await use_case.execute(SyncDataSourceRequest(data_source_id=data_source.id))
    assert isinstance(result, Err)
    assert result.error.code == "DATA_SOURCE_ALREADY_SYNCING"


@pytest.mark.asyncio
async def test_sync_data_source_disabled() -> None:
    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()

    data_source = DataSource(
        kb_id=uuid4(),
        name="Disabled Drive",
        status=DataSourceStatus.DISABLED,
    )
    await ds_repo.save(data_source)

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=MagicMock(),
        kb_repository=MagicMock(),
        attach_use_case=MagicMock(),
    )

    result = await use_case.execute(SyncDataSourceRequest(data_source_id=data_source.id))
    assert isinstance(result, Err)
    assert result.error.code == "DATA_SOURCE_DISABLED"


@pytest.mark.asyncio
async def test_sync_data_source_not_found() -> None:
    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=MagicMock(),
        kb_repository=MagicMock(),
        attach_use_case=MagicMock(),
    )

    result = await use_case.execute(SyncDataSourceRequest(data_source_id=uuid4()))
    assert isinstance(result, Err)
    assert result.error.code == "DATA_SOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_sync_data_source_partial_file_failure_resilience() -> None:
    ds_repo = InMemoryDataSourceRepository()
    run_repo = InMemoryDataSourceRunRepository()

    data_source = DataSource(
        kb_id=uuid4(),
        name="Resilient Drive",
    )
    await ds_repo.save(data_source)

    connector = InMemoryDataSourceConnector()
    connector.add_mock_file(external_id="ok-1", name="file1.txt", content=b"content 1")
    connector.add_mock_file(external_id="bad-2", name="file2.txt", content=b"corrupt")
    connector.add_mock_file(external_id="ok-3", name="file3.txt", content=b"content 3")

    registry = DataSourceConnectorRegistry()
    registry.register(DataSourceType.GOOGLE_DRIVE_FOLDER, connector)

    kb_repo = MagicMock()
    kb_repo.get_by_id = AsyncMock(return_value=MagicMock(documents={}))

    attach_use_case = MagicMock(spec=AttachAndStoreDocumentUseCase)

    async def fake_attach(
        req: AttachAndStoreDocumentRequest,
    ) -> Result[AttachAndStoreDocumentResponse, DomainError]:
        if req.file_name == "file2.txt":
            return Err(DomainError("Disk write failed", "ATTACH_FAILED"))
        return Ok(
            AttachAndStoreDocumentResponse(
                document_id=uuid4(),
                storage_path=f"path/{req.file_name}",
                status="UPLOADED",
            )
        )

    attach_use_case.execute = AsyncMock(side_effect=fake_attach)

    use_case = SyncDataSourceUseCase(
        data_source_repository=ds_repo,
        data_source_run_repository=run_repo,
        connector_registry=registry,
        kb_repository=kb_repo,
        attach_use_case=attach_use_case,
    )

    result = await use_case.execute(SyncDataSourceRequest(data_source_id=data_source.id))
    assert isinstance(result, Ok)
    assert result.value.total_items_discovered == 3

    saved_run = await run_repo.get_by_id(result.value.sync_run_id)
    assert saved_run is not None
    assert saved_run.failed_files_count == 1
    assert len(saved_run.failure_summary) == 1
    assert saved_run.failure_summary[0]["file_name"] == "file2.txt"
