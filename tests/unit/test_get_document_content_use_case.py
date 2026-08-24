from uuid import uuid4

import pytest

from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.get_document_content import (
    GetDocumentContentRequest,
    GetDocumentContentUseCase,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)


@pytest.mark.asyncio
async def test_get_document_content_use_case_success(tmp_path: pytest.TempPathFactory) -> None:
    repo = InMemoryKnowledgeBaseRepository()
    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    use_case = GetDocumentContentUseCase(repo, storage)

    schema = OntologySchema(
        name="test_schema",
        description="desc",
        node_types=[],
        relationship_types=[],
    )
    kb = KnowledgeBaseAggregate.create("Test KB", "Description", schema)
    doc_id = kb.attach_document("architecture.md", "text/markdown")
    kb.mark_document_stored(doc_id, f"kb-{kb.id}/documents/{doc_id}.md", byte_size=1024)

    sample_md = (
        "# 1. Architecture Overview\n\n"
        "Here is the architecture.\n\n"
        "## 1.1 Storage Layer\n\n"
        "Storage details here.\n\n"
        "### 1.1.1 Local Object Storage\n\n"
        "Local file system adapter."
    )
    md_path = f"kb-{kb.id}/markdown/{doc_id}.md"
    await storage.put_object(md_path, sample_md.encode("utf-8"), "text/markdown")
    kb.mark_document_parsed(doc_id, md_path, sample_md[:200])
    await repo.save(kb)

    request = GetDocumentContentRequest(kb_id=kb.id, document_id=doc_id)
    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    resp = result.value
    assert resp.document_id == doc_id
    assert resp.kb_id == kb.id
    assert resp.file_name == "architecture.md"
    assert resp.status == "PARSED"
    assert resp.markdown_content == sample_md
    assert len(resp.toc_tree) == 3

    assert resp.toc_tree[0].level == 1
    assert resp.toc_tree[0].title == "1. Architecture Overview"
    assert resp.toc_tree[0].anchor == "1-architecture-overview"

    assert resp.toc_tree[1].level == 2
    assert resp.toc_tree[1].title == "1.1 Storage Layer"
    assert resp.toc_tree[1].anchor == "11-storage-layer"

    assert resp.toc_tree[2].level == 3
    assert resp.toc_tree[2].title == "1.1.1 Local Object Storage"
    assert resp.toc_tree[2].anchor == "111-local-object-storage"


@pytest.mark.asyncio
async def test_get_document_content_kb_not_found(tmp_path: pytest.TempPathFactory) -> None:
    repo = InMemoryKnowledgeBaseRepository()
    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    use_case = GetDocumentContentUseCase(repo, storage)

    request = GetDocumentContentRequest(kb_id=uuid4(), document_id=uuid4())
    result = await use_case.execute(request)

    assert isinstance(result, Err)
    assert result.error.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_document_content_doc_not_found(tmp_path: pytest.TempPathFactory) -> None:
    repo = InMemoryKnowledgeBaseRepository()
    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    use_case = GetDocumentContentUseCase(repo, storage)

    schema = OntologySchema(
        name="test_schema",
        description="desc",
        node_types=[],
        relationship_types=[],
    )
    kb = KnowledgeBaseAggregate.create("Test KB", "Description", schema)
    await repo.save(kb)

    request = GetDocumentContentRequest(kb_id=kb.id, document_id=uuid4())
    result = await use_case.execute(request)

    assert isinstance(result, Err)
    assert result.error.code == "NOT_FOUND"
