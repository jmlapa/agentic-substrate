from uuid import uuid4

import pytest

from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk
from src.modules.knowledge.domain.value_objects.structural_graph_document import (
    StructuralGraphDocument,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_graph_store import (
    InMemoryGraphStore,
)


@pytest.mark.asyncio
async def test_falkordb_hybrid_graph_integration_flow() -> None:
    store = InMemoryGraphStore()
    kb_id = uuid4()
    doc_id = uuid4()

    # 1. Ensure index
    await store.ensure_vector_index(kb_id, dimension=768, similarity_function="cosine")

    # 2. Ingest structural document
    p1 = ParentChunk(
        id="parent-1",
        header_path="# Chapter 1 > Section 1",
        content="This section explains data privacy laws and compliance requirements.",
        token_count=120,
    )
    c1 = ChildChunk(
        id="child-1",
        parent_chunk_id="parent-1",
        chunk_index=0,
        header_path="# Chapter 1 > Section 1",
        content="data privacy laws and compliance requirements",
        embedding=[0.1] * 768,
    )
    doc = StructuralGraphDocument(
        document_id=doc_id,
        document_name="compliance.md",
        parents=[p1],
        children=[c1],
    )
    nodes, edges = await store.store_structural_document(kb_id, doc)
    assert nodes == 3
    assert edges == 2

    # 3. Store parent mentions (conceptual entities)
    graph = ExtractedGraph(
        nodes=[
            GraphNode(
                id="entity-lgpd",
                node_type="Regulation",
                properties={"name": "LGPD", "scope": "National"},
            )
        ],
        edges=[],
    )
    m_nodes, m_edges = await store.store_parent_mentions(kb_id, "parent-1", graph)
    assert m_nodes == 1
    assert m_edges == 1

    # 4. Perform hybrid search
    results = await store.query_hybrid(kb_id, query_embedding=[0.1] * 768, top_k=5)
    assert len(results) == 1
    assert results[0].parent_chunk_id == "parent-1"
    assert "privacy laws" in results[0].parent_content
    assert len(results[0].related_entities) == 1
    assert results[0].related_entities[0]["type"] == "Regulation"
    assert results[0].related_entities[0]["properties"]["name"] == "LGPD"
