from uuid import uuid4

import pytest

from src.kernel.domain.result import Err, Ok
from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.modules.knowledge.application.use_cases.reprocess_document import (
    ReprocessDocumentRequest,
    ReprocessDocumentUseCase,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)


@pytest.mark.asyncio
async def test_reprocess_document_success_on_uploaded_or_failed_doc() -> None:
    bus = InMemoryEventBus()
    store = InMemoryEventStore(event_bus=bus)
    repo = InMemoryKnowledgeBaseRepository()

    kb = KnowledgeBaseAggregate.create(
        name="TestKB",
        description="Desc",
        ontology=OntologySchema(name="Onto", description="", node_types=[]),
    )
    await repo.save(kb)

    doc_id = kb.attach_document("test.pdf", "application/pdf")
    doc_info = kb.documents[doc_id]
    kb.mark_document_stored(doc_id, doc_info["storage_path"], 100)
    kb.mark_processing_failed(doc_id, step="PARSE_MARKDOWN", error_message="Network error")
    await repo.save(kb)
    await store.append_events(kb.id, "KnowledgeBaseAggregate", list(kb.uncommitted_events), 0)
    kb.mark_events_as_committed()

    use_case = ReprocessDocumentUseCase(
        event_store=store,
        repository=repo,
        event_bus=bus,
    )

    req = ReprocessDocumentRequest(kb_id=kb.id, document_id=doc_id)
    res = await use_case.execute(req)

    assert isinstance(res, Ok)
    assert res.value.document_id == doc_id
    assert res.value.status == "UPLOADED"

    # Verifica que o aggregate teve seu status atualizado
    updated_kb = await repo.get_by_id(kb.id)
    assert updated_kb is not None
    assert updated_kb.documents[doc_id]["error"] is None


@pytest.mark.asyncio
async def test_reprocess_document_not_found() -> None:
    bus = InMemoryEventBus()
    store = InMemoryEventStore(event_bus=bus)
    repo = InMemoryKnowledgeBaseRepository()

    use_case = ReprocessDocumentUseCase(
        event_store=store,
        repository=repo,
        event_bus=bus,
    )

    req = ReprocessDocumentRequest(kb_id=uuid4(), document_id=uuid4())
    res = await use_case.execute(req)

    assert isinstance(res, Err)
    assert res.error.code == "NOT_FOUND"
