from uuid import uuid4

import pytest

from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.quick_search_notes import (
    QuickSearchNotesRequest,
    QuickSearchNotesUseCase,
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
async def test_quick_search_notes_finds_title_and_header(tmp_path: pytest.TempPathFactory) -> None:
    repo = InMemoryKnowledgeBaseRepository()
    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    use_case = QuickSearchNotesUseCase(repo, storage)

    schema = OntologySchema(name="schema", description="desc", node_types=[], relationship_types=[])
    kb = KnowledgeBaseAggregate.create("Engineering KB", "Docs", schema)

    doc_id = kb.attach_document("architecture_guide.md", "text/markdown")
    kb.mark_document_stored(doc_id, f"kb-{kb.id}/documents/{doc_id}.md", byte_size=2048)
    kb.mark_document_parsed(doc_id, f"kb-{kb.id}/markdown/{doc_id}.md", "# 1. Architecture")
    kb.mark_document_chunked(
        doc_id,
        total_parents=2,
        total_children=4,
        chunks_summary=[
            {
                "parent_id": f"{doc_id}-p1",
                "header_path": (
                    "[Doc: architecture_guide.md] > # 1. Architecture > ## 1.1 Storage Layer"
                ),
                "token_count": 850,
            },
            {
                "parent_id": f"{doc_id}-p2",
                "header_path": "[Doc: architecture_guide.md] > # 2. FalkorDB Hybrid Engine",
                "token_count": 920,
            },
        ],
    )
    await repo.save(kb)

    # 1. Busca por título
    req_title = QuickSearchNotesRequest(kb_id=kb.id, query="architecture")
    res_title = await use_case.execute(req_title)
    assert isinstance(res_title, Ok)
    assert len(res_title.value.results) >= 1
    title_match = next((r for r in res_title.value.results if r.match_type == "title"), None)
    assert title_match is not None
    assert title_match.document_name == "architecture_guide.md"

    # 2. Busca por cabeçalho
    req_header = QuickSearchNotesRequest(kb_id=kb.id, query="Storage Layer")
    res_header = await use_case.execute(req_header)
    assert isinstance(res_header, Ok)
    assert len(res_header.value.results) == 1
    assert res_header.value.results[0].match_type == "header"
    assert res_header.value.results[0].matched_title == "1.1 Storage Layer"
    assert res_header.value.results[0].anchor == "11-storage-layer"


@pytest.mark.asyncio
async def test_quick_search_notes_kb_not_found(tmp_path: pytest.TempPathFactory) -> None:
    repo = InMemoryKnowledgeBaseRepository()
    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    use_case = QuickSearchNotesUseCase(repo, storage)

    req = QuickSearchNotesRequest(kb_id=uuid4(), query="test")
    res = await use_case.execute(req)
    assert isinstance(res, Err)
    assert res.error.code == "NOT_FOUND"
