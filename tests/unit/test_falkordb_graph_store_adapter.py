from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.infrastructure.adapters.falkordb_graph_store_adapter import (
    FalkorDbGraphStoreAdapter,
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
    assert mock_graph_handle.query.call_count == 3  # 2 nodes + 1 edge


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
