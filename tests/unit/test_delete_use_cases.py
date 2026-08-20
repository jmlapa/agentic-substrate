from uuid import uuid4

import pytest

from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.delete_document import (
    DeleteDocumentRequest,
    DeleteDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.delete_knowledge_base import (
    DeleteKnowledgeBaseRequest,
    DeleteKnowledgeBaseUseCase,
)
from src.modules.knowledge.application.use_cases.delete_ontology_template import (
    DeleteOntologyTemplateRequest,
    DeleteOntologyTemplateUseCase,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.ontology.ontology_template import OntologyTemplate
from src.modules.knowledge.infrastructure.adapters.in_memory_graph_store import (
    InMemoryGraphStore,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_ontology_repository import (
    InMemoryOntologyRepository,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)


@pytest.mark.asyncio
async def test_delete_knowledge_base_success(tmp_path: pytest.TempPathFactory) -> None:
    repo = InMemoryKnowledgeBaseRepository()
    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    graph_store = InMemoryGraphStore()

    kb = KnowledgeBaseAggregate.create(
        name="Test KB",
        description="To be deleted",
        ontology=OntologySchema(name="Test", description="", node_types=[], relationship_types=[]),
    )
    await repo.save(kb)

    # Put a dummy file in storage partition
    await storage.put_object(f"{kb.storage_partition}/raw/test.txt", b"content", "text/plain")
    assert await storage.exists(f"{kb.storage_partition}/raw/test.txt")

    use_case = DeleteKnowledgeBaseUseCase(
        repository=repo,
        object_storage=storage,
        graph_store=graph_store,
    )

    res = await use_case.execute(DeleteKnowledgeBaseRequest(kb_id=kb.id))
    assert isinstance(res, Ok)
    assert res.value.success is True
    assert res.value.kb_id == kb.id

    # Verificações
    assert await repo.get_by_id(kb.id) is None
    assert not await storage.exists(f"{kb.storage_partition}/raw/test.txt")


@pytest.mark.asyncio
async def test_delete_knowledge_base_not_found() -> None:
    repo = InMemoryKnowledgeBaseRepository()
    storage = LocalFileSystemStorageAdapter()
    graph_store = InMemoryGraphStore()

    use_case = DeleteKnowledgeBaseUseCase(
        repository=repo,
        object_storage=storage,
        graph_store=graph_store,
    )

    res = await use_case.execute(DeleteKnowledgeBaseRequest(kb_id=uuid4()))
    assert isinstance(res, Err)
    assert res.error.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_document_success(tmp_path: pytest.TempPathFactory) -> None:
    repo = InMemoryKnowledgeBaseRepository()
    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    graph_store = InMemoryGraphStore()

    kb = KnowledgeBaseAggregate.create(
        name="Test KB",
        description="With document",
        ontology=OntologySchema(name="Test", description="", node_types=[], relationship_types=[]),
    )
    doc_id = kb.attach_document("sample.pdf", "application/pdf")
    await repo.save(kb)

    # Put dummy files
    raw_path = f"{kb.storage_partition}/raw/{doc_id}-sample.pdf"
    await storage.put_object(raw_path, b"pdf", "application/pdf")
    assert await storage.exists(raw_path)

    use_case = DeleteDocumentUseCase(
        repository=repo,
        object_storage=storage,
        graph_store=graph_store,
    )

    res = await use_case.execute(DeleteDocumentRequest(kb_id=kb.id, document_id=doc_id))
    assert isinstance(res, Ok)
    assert res.value.success is True
    assert res.value.document_id == doc_id

    # Verify document removed from KB aggregate
    loaded_kb = await repo.get_by_id(kb.id)
    assert loaded_kb is not None
    assert doc_id not in loaded_kb.documents
    assert not await storage.exists(raw_path)


@pytest.mark.asyncio
async def test_delete_ontology_template_success() -> None:
    repo = InMemoryOntologyRepository()
    tpl = OntologyTemplate(
        id=uuid4(),
        name="Free Template",
        description="Not used by any KB",
        version=1,
        node_types=[],
        relationship_types=[],
    )
    await repo.save(tpl)

    use_case = DeleteOntologyTemplateUseCase(repository=repo)
    res = await use_case.execute(DeleteOntologyTemplateRequest(ontology_id=tpl.id))
    assert isinstance(res, Ok)
    assert res.value.success is True
    assert await repo.get_by_id(tpl.id) is None


@pytest.mark.asyncio
async def test_delete_ontology_template_conflict_when_in_use() -> None:
    class InUseOntologyRepository(InMemoryOntologyRepository):
        async def count_usages(self, ontology_id: uuid4) -> int:  # type: ignore[valid-type]
            return 2

    repo = InUseOntologyRepository()
    tpl = OntologyTemplate(
        id=uuid4(),
        name="In Use Template",
        description="Used by 2 KBs",
        version=1,
        node_types=[],
        relationship_types=[],
    )
    await repo.save(tpl)

    use_case = DeleteOntologyTemplateUseCase(repository=repo)
    res = await use_case.execute(DeleteOntologyTemplateRequest(ontology_id=tpl.id))
    assert isinstance(res, Err)
    assert res.error.code == "CONFLICT"
    assert "2 Knowledge Base(s)" in res.error.message
