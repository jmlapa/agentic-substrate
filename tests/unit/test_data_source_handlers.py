from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.domain.domain_event import DomainEvent
from src.kernel.domain.result import Ok
from src.modules.knowledge.application.handlers.blue_green_document_swap_handler import (
    BlueGreenDocumentSwapHandler,
)
from src.modules.knowledge.application.handlers.data_source_run_projector import (
    DataSourceRunProjector,
)
from src.modules.knowledge.application.use_cases.delete_document import (
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    DeleteDocumentUseCase,
)
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
from src.modules.knowledge.domain.value_objects.data_source_run_status import (
    DataSourceRunStatus,
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
async def test_blue_green_swap_with_replaces_doc_id() -> None:
    kb_id = uuid4()
    new_doc_id = uuid4()
    old_doc_id = uuid4()

    mock_delete_uc = MagicMock(spec=DeleteDocumentUseCase)
    mock_delete_uc.execute = AsyncMock(
        return_value=Ok(
            DeleteDocumentResponse(
                document_id=old_doc_id,
                success=True,
                message="Deleted",
            )
        )
    )

    handler = BlueGreenDocumentSwapHandler(delete_use_case=mock_delete_uc)

    event = DocumentKnowledgeIndexedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=new_doc_id,
        indexed_nodes_count=10,
        indexed_edges_count=12,
        metadata={"replaces_doc_id": str(old_doc_id)},
    )

    await handler.handle(event)

    mock_delete_uc.execute.assert_awaited_once()
    called_request: DeleteDocumentRequest = mock_delete_uc.execute.call_args[0][0]
    assert called_request.kb_id == kb_id
    assert called_request.document_id == old_doc_id


@pytest.mark.asyncio
async def test_blue_green_swap_no_replaces_doc_id_noop() -> None:
    mock_delete_uc = MagicMock(spec=DeleteDocumentUseCase)
    mock_delete_uc.execute = AsyncMock()

    handler = BlueGreenDocumentSwapHandler(delete_use_case=mock_delete_uc)

    event = DocumentKnowledgeIndexedEvent(
        aggregate_id=uuid4(),
        aggregate_type="KnowledgeBaseAggregate",
        document_id=uuid4(),
        indexed_nodes_count=5,
        indexed_edges_count=3,
        metadata={},  # No replaces_doc_id
    )

    await handler.handle(event)

    mock_delete_uc.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_data_source_run_projector_increments_indexed_count_and_completes() -> None:
    run_repo = InMemoryDataSourceRunRepository()
    event_bus = DummyEventBus()

    data_source_id = uuid4()
    kb_id = uuid4()

    run = DataSourceRun(
        data_source_id=data_source_id,
        kb_id=kb_id,
        status=DataSourceRunStatus.INGESTING,
        total_files_discovered=2,
    )
    await run_repo.save(run)

    projector = DataSourceRunProjector(
        data_source_run_repository=run_repo,
        event_bus=event_bus,
    )

    # First document indexed
    event1 = DocumentKnowledgeIndexedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=uuid4(),
        indexed_nodes_count=5,
        indexed_edges_count=2,
        metadata={"sync_run_id": str(run.id)},
    )
    await projector.handle(event1)

    r1 = await run_repo.get_by_id(run.id)
    assert r1 is not None
    assert r1.indexed_files_count == 1
    assert r1.completed_at is None
    assert len(event_bus.published) == 0

    # Second document indexed -> completes run!
    event2 = DocumentKnowledgeIndexedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=uuid4(),
        indexed_nodes_count=8,
        indexed_edges_count=4,
        metadata={"sync_run_id": str(run.id)},
    )
    await projector.handle(event2)

    r2 = await run_repo.get_by_id(run.id)
    assert r2 is not None
    assert r2.indexed_files_count == 2
    assert r2.status == DataSourceRunStatus.COMPLETED
    assert r2.completed_at is not None

    assert len(event_bus.published) == 1
    completed_event = event_bus.published[0]
    assert isinstance(completed_event, DataSourceRunCompletedEvent)
    assert completed_event.run_id == run.id
    assert completed_event.status == "COMPLETED"
    assert completed_event.indexed_files == 2
    assert completed_event.failed_files == 0


@pytest.mark.asyncio
async def test_data_source_run_projector_partial_failure() -> None:
    run_repo = InMemoryDataSourceRunRepository()
    event_bus = DummyEventBus()

    data_source_id = uuid4()
    kb_id = uuid4()

    run = DataSourceRun(
        data_source_id=data_source_id,
        kb_id=kb_id,
        status=DataSourceRunStatus.INGESTING,
        total_files_discovered=2,
    )
    await run_repo.save(run)

    projector = DataSourceRunProjector(
        data_source_run_repository=run_repo,
        event_bus=event_bus,
    )

    # 1 success
    await projector.handle(
        DocumentKnowledgeIndexedEvent(
            aggregate_id=kb_id,
            aggregate_type="KnowledgeBaseAggregate",
            document_id=uuid4(),
            indexed_nodes_count=5,
            indexed_edges_count=2,
            metadata={"sync_run_id": str(run.id)},
        )
    )

    # 1 failure
    bad_doc_id = uuid4()
    await projector.handle(
        DocumentProcessingFailedEvent(
            aggregate_id=kb_id,
            aggregate_type="KnowledgeBaseAggregate",
            document_id=bad_doc_id,
            step="CHUNKING",
            error_message="SyntaxError in PDF",
            metadata={"sync_run_id": str(run.id), "file_name": "corrupt.pdf"},
        )
    )

    r = await run_repo.get_by_id(run.id)
    assert r is not None
    assert r.indexed_files_count == 1
    assert r.failed_files_count == 1
    assert r.status == DataSourceRunStatus.PARTIALLY_FAILED
    assert r.completed_at is not None
    assert len(r.failure_summary) == 1
    assert r.failure_summary[0]["file_name"] == "corrupt.pdf"

    assert len(event_bus.published) == 1
    assert isinstance(event_bus.published[0], DataSourceRunCompletedEvent)
    assert event_bus.published[0].status == "PARTIALLY_FAILED"


@pytest.mark.asyncio
async def test_data_source_run_projector_total_failure() -> None:
    run_repo = InMemoryDataSourceRunRepository()
    event_bus = DummyEventBus()

    run = DataSourceRun(
        data_source_id=uuid4(),
        kb_id=uuid4(),
        status=DataSourceRunStatus.INGESTING,
        total_files_discovered=1,
    )
    await run_repo.save(run)

    projector = DataSourceRunProjector(
        data_source_run_repository=run_repo,
        event_bus=event_bus,
    )

    await projector.handle(
        DocumentProcessingFailedEvent(
            aggregate_id=uuid4(),
            aggregate_type="KnowledgeBaseAggregate",
            document_id=uuid4(),
            step="OCR",
            error_message="VLM timeout",
            metadata={"sync_run_id": str(run.id), "file_name": "scan.png"},
        )
    )

    r = await run_repo.get_by_id(run.id)
    assert r is not None
    assert r.status == DataSourceRunStatus.FAILED
    assert r.completed_at is not None

    assert len(event_bus.published) == 1
    ev = event_bus.published[0]
    assert isinstance(ev, DataSourceRunCompletedEvent)
    assert ev.status == "FAILED"
