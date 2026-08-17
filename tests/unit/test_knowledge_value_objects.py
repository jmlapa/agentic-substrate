from uuid import uuid4

from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk
from src.modules.knowledge.domain.value_objects.structural_graph_document import (
    StructuralGraphDocument,
)


def test_hybrid_search_result_instantiation() -> None:
    result = HybridSearchResult(
        parent_chunk_id="parent-123",
        header_path="# Title > Section",
        parent_content="Full context text of the parent chunk.",
        relevance_score=0.88,
        related_entities=[{"type": "Company", "properties": {"name": "Acme Corp"}}],
    )
    assert result.parent_chunk_id == "parent-123"
    assert result.header_path == "# Title > Section"
    assert result.parent_content == "Full context text of the parent chunk."
    assert result.relevance_score == 0.88
    assert len(result.related_entities) == 1
    assert result.related_entities[0]["type"] == "Company"


def test_structural_graph_document_instantiation() -> None:
    doc_id = uuid4()
    parent = ParentChunk(
        id="p1",
        header_path="# Header",
        content="Parent content",
        token_count=100,
    )
    child = ChildChunk(
        id="c1",
        parent_chunk_id="p1",
        chunk_index=0,
        header_path="# Header",
        content="Child content",
        embedding=[0.1, 0.2, 0.3],
    )
    doc = StructuralGraphDocument(
        document_id=doc_id,
        document_name="spec.md",
        parents=[parent],
        children=[child],
    )
    assert doc.document_id == doc_id
    assert doc.document_name == "spec.md"
    assert len(doc.parents) == 1
    assert len(doc.children) == 1
    assert doc.children[0].embedding == [0.1, 0.2, 0.3]
