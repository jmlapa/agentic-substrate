from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.domain.domain_error import DomainError
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.value_objects.document_source_type import (
    DocumentSourceType,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.infrastructure.adapters.postgres_document_repository import (
    PostgresDocumentRepository,
)


@pytest.mark.asyncio
async def test_save_and_load_new_document() -> None:
    event_store = InMemoryEventStore()
    repo = PostgresDocumentRepository(event_store=event_store)

    doc_id = uuid4()
    kb_id = uuid4()
    doc = DocumentAggregate.create(
        document_id=doc_id,
        kb_id=kb_id,
        file_name="spec.pdf",
        content_type="application/pdf",
        storage_path=f"kb-{kb_id}/raw/{doc_id}-spec.pdf",
        enable_ocr=True,
        ocr_instructions="Preserve tables",
        source_type=DocumentSourceType.DOCUMENT,
        metadata={"user": "tester"},
    )
    assert len(doc.uncommitted_events) == 1
    assert doc.version == 1

    await repo.save(doc)
    assert len(doc.uncommitted_events) == 0
    assert doc.version == 1

    loaded = await repo.load(doc_id)
    assert loaded is not None
    assert loaded.id == doc_id
    assert loaded.kb_id == kb_id
    assert loaded.file_name == "spec.pdf"
    assert loaded.content_type == "application/pdf"
    assert loaded.status == DocumentStatus.PENDING_UPLOAD
    assert loaded.enable_ocr is True
    assert loaded.ocr_instructions == "Preserve tables"
    assert loaded.metadata == {"user": "tester"}
    assert loaded.version == 1


@pytest.mark.asyncio
async def test_save_incremental_events_advances_version() -> None:
    event_store = InMemoryEventStore()
    repo = PostgresDocumentRepository(event_store=event_store)

    doc_id = uuid4()
    kb_id = uuid4()
    doc = DocumentAggregate.create(
        document_id=doc_id,
        kb_id=kb_id,
        file_name="notes.md",
        content_type="text/markdown",
        storage_path="path/notes.md",
    )
    await repo.save(doc)

    # Next step: mark stored
    doc.mark_stored(storage_path="path/notes.md", byte_size=2048)
    assert doc.version == 2
    await repo.save(doc)

    # Next step: mark parsed
    doc.mark_parsed(
        markdown_storage_path="path/notes.parsed.md",
        markdown_preview="# Notes",
    )
    assert doc.version == 3
    await repo.save(doc)

    # Re-load from repository
    loaded = await repo.get_by_id(doc_id)
    assert loaded is not None
    assert loaded.status == DocumentStatus.PARSED
    assert loaded.byte_size == 2048
    assert loaded.markdown_storage_path == "path/notes.parsed.md"
    assert loaded.markdown_preview == "# Notes"
    assert loaded.version == 3


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_empty() -> None:
    event_store = InMemoryEventStore()
    repo = PostgresDocumentRepository(event_store=event_store)

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_save_empty_uncommitted_events_is_noop() -> None:
    event_store = InMemoryEventStore()
    repo = PostgresDocumentRepository(event_store=event_store)

    doc = DocumentAggregate(id=uuid4())
    # No events recorded
    await repo.save(doc)
    events = await event_store.get_events(doc.id)
    assert len(events) == 0


@pytest.mark.asyncio
async def test_concurrency_conflict_detected() -> None:
    event_store = InMemoryEventStore()
    repo = PostgresDocumentRepository(event_store=event_store)

    doc_id = uuid4()
    kb_id = uuid4()
    doc1 = DocumentAggregate.create(
        document_id=doc_id,
        kb_id=kb_id,
        file_name="doc.pdf",
        content_type="application/pdf",
        storage_path="path/doc.pdf",
    )
    await repo.save(doc1)

    # Load into two separate instances
    instance_a = await repo.load(doc_id)
    instance_b = await repo.load(doc_id)
    assert instance_a is not None and instance_b is not None

    # Instance A updates first
    instance_a.mark_stored("path/doc.pdf", 100)
    await repo.save(instance_a)

    # Instance B tries to update with stale version
    instance_b.mark_stored("path/doc.pdf", 200)
    with pytest.raises(DomainError) as exc_info:
        await repo.save(instance_b)

    assert exc_info.value.code == "CONCURRENCY_ERROR"


@pytest.mark.asyncio
async def test_delete_by_id_records_deletion_and_deletes_relational() -> None:
    event_store = InMemoryEventStore()
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    repo = PostgresDocumentRepository(event_store=event_store, pool=mock_pool)

    doc_id = uuid4()
    kb_id = uuid4()
    doc = DocumentAggregate.create(
        document_id=doc_id,
        kb_id=kb_id,
        file_name="to_delete.txt",
        content_type="text/plain",
        storage_path="path/to_delete.txt",
    )
    await repo.save(doc)

    await repo.delete_by_id(doc_id)

    # Check relational delete executed
    mock_conn.execute.assert_awaited_once_with(
        "DELETE FROM attached_documents WHERE id = $1;", doc_id
    )

    # Check event stream recorded deletion
    events = await event_store.get_events(doc_id)
    assert len(events) == 2
    assert events[-1].event_type == "DocumentDeletedEvent"


@pytest.mark.asyncio
async def test_knowledge_base_aggregate_delegates_document_creation() -> None:
    kb = KnowledgeBaseAggregate(id=uuid4())
    kb.storage_partition = f"kb-{kb.id}"

    doc = kb.create_document(
        file_name="architecture.pdf",
        content_type="application/pdf",
        enable_ocr=True,
    )

    assert isinstance(doc, DocumentAggregate)
    assert doc.kb_id == kb.id
    assert doc.file_name == "architecture.pdf"
    assert doc.enable_ocr is True
    assert doc.storage_path == f"{kb.storage_partition}/raw/{doc.id}-architecture.pdf"
    assert len(doc.uncommitted_events) == 1
