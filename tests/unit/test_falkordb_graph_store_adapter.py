from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk
from src.modules.knowledge.domain.value_objects.structural_graph_document import (
    StructuralGraphDocument,
)
from src.modules.knowledge.infrastructure.adapters.falkordb_graph_store_adapter import (
    FalkorDbGraphStoreAdapter,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_graph_store import (
    InMemoryGraphStore,
)


@pytest.mark.asyncio
async def test_falkordb_graph_store_implements_protocol() -> None:
    mock_client = MagicMock()
    adapter = FalkorDbGraphStoreAdapter(client=mock_client)
    assert isinstance(adapter, IGraphStore)


@pytest.mark.asyncio
async def test_falkordb_graph_store_stores_nodes_and_edges() -> None:
    mock_client = MagicMock()
    mock_graph_handle = MagicMock()
    mock_client.select_graph.return_value = mock_graph_handle

    adapter = FalkorDbGraphStoreAdapter(client=mock_client)
    kb_id = uuid4()
    graph = ExtractedGraph(
        nodes=[
            GraphNode(id="n1", node_type="Company", properties={"name": "Acme Inc"}),
            GraphNode(id="n2", node_type="Person", properties={"name": "Alice"}),
        ],
        edges=[
            GraphEdge(
                source_id="n2",
                target_id="n1",
                relationship_type="WORKS_AT",
                properties={"role": "Engineer"},
            )
        ],
    )

    nodes_count, edges_count = await adapter.store_graph(kb_id, graph)
    assert nodes_count == 2
    assert edges_count == 1
    assert mock_graph_handle.query.call_count == 3


@pytest.mark.asyncio
async def test_falkordb_graph_store_empty_graph_noop() -> None:
    mock_client = MagicMock()
    adapter = FalkorDbGraphStoreAdapter(client=mock_client)
    nodes_count, edges_count = await adapter.store_graph(
        uuid4(), ExtractedGraph(nodes=[], edges=[])
    )
    assert nodes_count == 0
    assert edges_count == 0
    assert not mock_client.select_graph.called


@pytest.mark.asyncio
async def test_falkordb_graph_store_ensure_vector_index() -> None:
    mock_client = MagicMock()
    mock_graph_handle = MagicMock()
    mock_client.select_graph.return_value = mock_graph_handle

    adapter = FalkorDbGraphStoreAdapter(client=mock_client)
    kb_id = uuid4()
    await adapter.ensure_vector_index(kb_id, dimension=768, similarity_function="cosine")

    assert mock_client.select_graph.called
    assert mock_graph_handle.query.called
    query_str = mock_graph_handle.query.call_args[0][0]
    assert "CREATE VECTOR INDEX FOR (c:ChildChunk)" in query_str


@pytest.mark.asyncio
async def test_falkordb_graph_store_store_structural_document() -> None:
    mock_client = MagicMock()
    mock_graph_handle = MagicMock()
    mock_client.select_graph.return_value = mock_graph_handle

    adapter = FalkorDbGraphStoreAdapter(client=mock_client)
    kb_id = uuid4()
    doc_id = uuid4()

    parent = ParentChunk(
        id="p1",
        header_path="# Title",
        content="Parent full content",
        token_count=50,
    )
    child = ChildChunk(
        id="c1",
        parent_chunk_id="p1",
        chunk_index=0,
        header_path="# Title",
        content="Child content",
        embedding=[0.1, 0.2, 0.3],
    )
    doc = StructuralGraphDocument(
        document_id=doc_id,
        document_name="test.md",
        parents=[parent],
        children=[child],
    )

    nodes, edges = await adapter.store_structural_document(kb_id, doc)
    assert nodes == 3  # 1 doc + 1 parent + 1 child
    assert edges == 2  # 1 HAS_PARENT + 1 CONTAINS_CHILD
    assert mock_graph_handle.query.call_count == 3


@pytest.mark.asyncio
async def test_falkordb_graph_store_store_parent_mentions() -> None:
    mock_client = MagicMock()
    mock_graph_handle = MagicMock()
    mock_client.select_graph.return_value = mock_graph_handle

    adapter = FalkorDbGraphStoreAdapter(client=mock_client)
    kb_id = uuid4()
    graph = ExtractedGraph(
        nodes=[GraphNode(id="e1", node_type="Law", properties={"name": "LGPD"})],
        edges=[],
    )

    nodes, edges = await adapter.store_parent_mentions(kb_id, "p1", graph)
    assert nodes == 1
    assert edges == 1  # 1 MENTIONS edge
    assert mock_graph_handle.query.call_count == 2  # 1 merge node + 1 merge mentions edge


@pytest.mark.asyncio
async def test_falkordb_graph_store_query_hybrid() -> None:
    mock_client = MagicMock()
    mock_graph_handle = MagicMock()
    mock_res = MagicMock()
    mock_res.result_set = [
        [
            "p1",
            "# Chapter 1",
            "Full text of parent 1",
            [{"type": "Law", "properties": {"name": "LGPD"}}],
            0.96,
        ]
    ]
    mock_graph_handle.query.return_value = mock_res
    mock_client.select_graph.return_value = mock_graph_handle

    adapter = FalkorDbGraphStoreAdapter(client=mock_client)
    kb_id = uuid4()
    results = await adapter.query_hybrid(kb_id, [0.1, 0.2, 0.3], top_k=5)

    assert len(results) == 1
    assert results[0].parent_chunk_id == "p1"
    assert results[0].header_path == "# Chapter 1"
    assert results[0].parent_content == "Full text of parent 1"
    assert results[0].relevance_score == 0.96
    assert len(results[0].related_entities) == 1
    assert results[0].related_entities[0]["type"] == "Law"


@pytest.mark.asyncio
async def test_in_memory_graph_store_hybrid_flow() -> None:
    store = InMemoryGraphStore()
    kb_id = uuid4()
    doc_id = uuid4()

    parent = ParentChunk(id="p1", header_path="# Sec", content="Parent txt", token_count=10)
    child = ChildChunk(
        id="c1", parent_chunk_id="p1", chunk_index=0, header_path="# Sec", content="Child txt"
    )
    doc = StructuralGraphDocument(
        document_id=doc_id, document_name="doc.md", parents=[parent], children=[child]
    )

    await store.store_structural_document(kb_id, doc)
    await store.store_parent_mentions(
        kb_id,
        "p1",
        ExtractedGraph(
            nodes=[GraphNode(id="e1", node_type="Concept", properties={"name": "Security"})],
            edges=[],
        ),
    )

    results = await store.query_hybrid(kb_id, [0.1, 0.2], top_k=5)
    assert len(results) == 1
    assert results[0].parent_chunk_id == "p1"
    assert results[0].parent_content == "Parent txt"
    assert len(results[0].related_entities) == 1


@pytest.mark.asyncio
async def test_falkordb_graph_store_query_subgraph() -> None:
    mock_client = MagicMock()
    mock_graph_handle = MagicMock()
    mock_item = MagicMock()
    mock_item.properties = {"id": "n1", "name": "Acme Inc"}
    mock_item.labels = ["Company"]

    mock_res = MagicMock()
    mock_res.result_set = [[mock_item]]
    mock_graph_handle.query.return_value = mock_res
    mock_client.select_graph.return_value = mock_graph_handle

    adapter = FalkorDbGraphStoreAdapter(client=mock_client)
    results = await adapter.query_subgraph(uuid4(), "MATCH (n) RETURN n", top_k=5)

    assert len(results) == 1
    assert results[0]["id"] == "n1"
    assert results[0]["node_type"] == "Company"
    assert results[0]["properties"] == {"id": "n1", "name": "Acme Inc"}
