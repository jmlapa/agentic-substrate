from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.knowledge.domain.interfaces.i_vector_store import IVectorStore
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.infrastructure.adapters.pgvector_store_adapter import (
    PgVectorStoreAdapter,
)


class MockAcquire:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    async def __aenter__(self) -> Any:
        return self.conn

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


@pytest.mark.asyncio
async def test_pgvector_store_implements_protocol() -> None:
    pool = MagicMock()
    adapter = PgVectorStoreAdapter(pool=pool)
    assert isinstance(adapter, IVectorStore)


@pytest.mark.asyncio
async def test_pgvector_store_initialize_schema() -> None:
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockAcquire(mock_conn)

    adapter = PgVectorStoreAdapter(pool=mock_pool, embedding_dimension=1536)
    await adapter.initialize_schema()

    mock_conn.execute.assert_called_once()
    assert "CREATE EXTENSION IF NOT EXISTS vector" in mock_conn.execute.call_args[0][0]
    assert "vector(1536)" in mock_conn.execute.call_args[0][0]


@pytest.mark.asyncio
async def test_pgvector_store_node_embeddings() -> None:
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockAcquire(mock_conn)

    adapter = PgVectorStoreAdapter(pool=mock_pool)
    kb_id = uuid4()
    graph = ExtractedGraph(
        nodes=[
            GraphNode(id="node-1", node_type="Article", properties={"title": "Art 1"}),
            GraphNode(
                id="node-2",
                node_type="Concept",
                properties={"title": "Concept 1", "_embedding": [0.1, 0.2]},
            ),
        ],
        edges=[],
    )

    count = await adapter.store_node_embeddings(kb_id, graph)
    assert count == 2
    mock_conn.executemany.assert_called_once()


@pytest.mark.asyncio
async def test_pgvector_store_empty_nodes_noop() -> None:
    mock_pool = MagicMock()
    adapter = PgVectorStoreAdapter(pool=mock_pool)
    count = await adapter.store_node_embeddings(uuid4(), ExtractedGraph(nodes=[], edges=[]))
    assert count == 0
    assert not mock_pool.acquire.called


@pytest.mark.asyncio
async def test_pgvector_search_similar_nodes() -> None:
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": "node-1",
            "score": 0.88,
            "node_type": "Article",
            "properties": '{"title": "Art 1"}',
        }
    ]
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockAcquire(mock_conn)

    adapter = PgVectorStoreAdapter(pool=mock_pool)
    results = await adapter.search_similar_nodes(uuid4(), [0.1, 0.2, 0.3], top_k=3)

    assert len(results) == 1
    assert results[0]["id"] == "node-1"
    assert results[0]["score"] == 0.88
    assert results[0]["properties"] == {"title": "Art 1"}
