from uuid import uuid4

import pytest

from src.kernel.domain.result import Err, Ok
from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.modules.knowledge.application.use_cases.reprocess_document import (
    ReprocessDocumentRequest,
    ReprocessDocumentUseCase,
)
from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.infrastructure.adapters.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)


@pytest.mark.asyncio
async def test_reprocess_document_success_on_uploaded_or_failed_doc() -> None:
    bus = InMemoryEventBus()
    store = InMemoryEventStore(event_bus=bus)
    kb_repo = InMemoryKnowledgeBaseRepository()
    doc_repo = InMemoryDocumentRepository()

    kb = KnowledgeBaseAggregate.create(
        name="TestKB",
        description="Desc",
        ontology=OntologySchema(name="Onto", description="", node_types=[]),
    )
    await kb_repo.save(kb)

    doc_id = uuid4()
    doc = DocumentAggregate.create(
        document_id=doc_id,
        kb_id=kb.id,
        file_name="test.pdf",
        content_type="application/pdf",
        storage_path=f"{kb.storage_partition}/raw/{doc_id}-test.pdf",
    )
    doc.mark_stored(doc.storage_path, 100)
    doc.mark_processing_failed(step="PARSE_MARKDOWN", error_message="Network error")
    await doc_repo.save(doc)

    use_case = ReprocessDocumentUseCase(
        event_store=store,
        repository=kb_repo,
        event_bus=bus,
        document_repo=doc_repo,
    )

    req = ReprocessDocumentRequest(kb_id=kb.id, document_id=doc_id)
    res = await use_case.execute(req)

    assert isinstance(res, Ok)
    assert res.value.document_id == doc_id
    assert res.value.status == "UPLOADED"

    # Verifica que o aggregate soberano do documento teve seu status atualizado
    updated_doc = await doc_repo.get_by_id(doc_id)
    assert updated_doc is not None
    assert updated_doc.status == DocumentStatus.UPLOADED
    assert updated_doc.error_message is None


@pytest.mark.asyncio
async def test_reprocess_document_not_found() -> None:
    bus = InMemoryEventBus()
    store = InMemoryEventStore(event_bus=bus)
    kb_repo = InMemoryKnowledgeBaseRepository()
    doc_repo = InMemoryDocumentRepository()

    use_case = ReprocessDocumentUseCase(
        event_store=store,
        repository=kb_repo,
        event_bus=bus,
        document_repo=doc_repo,
    )

    req = ReprocessDocumentRequest(kb_id=uuid4(), document_id=uuid4())
    res = await use_case.execute(req)

    assert isinstance(res, Err)
    assert res.error.code == "NOT_FOUND"
