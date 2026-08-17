from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.knowledge.domain.interfaces.i_vector_store import IVectorStore
from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk
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


@pytest.mark.asyncio
async def test_pgvector_store_document_chunks() -> None:
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockAcquire(mock_conn)

    adapter = PgVectorStoreAdapter(pool=mock_pool, embedding_dimension=768)
    kb_id = uuid4()
    doc_id = uuid4()

    parent = ParentChunk(
        id="p-1",
        header_path="# Section",
        content="# Section\nFull parent content here.",
    )
    children = [
        ChildChunk(
            id="p-1-c1",
            parent_chunk_id="p-1",
            chunk_index=0,
            header_path="# Section",
            content="Child content",
            embedding=[0.1] * 768,
        )
    ]

    count = await adapter.store_document_chunks(
        kb_id=kb_id,
        document_id=doc_id,
        chunks=children,
        parent_chunks=[parent],
    )
    assert count == 1
    mock_conn.executemany.assert_called_once()


@pytest.mark.asyncio
async def test_pgvector_search_similar_chunks_with_filters() -> None:
    mock_conn = AsyncMock()
    doc_id = uuid4()
    mock_conn.fetch.return_value = [
        {
            "id": "p-1-c1",
            "document_id": doc_id,
            "parent_chunk_id": "p-1",
            "chunk_index": 0,
            "header_path": "# Section",
            "content": "Child content",
            "parent_content": "# Section\nFull parent content here.",
            "metadata": '{"tag": "test"}',
            "score": 0.94,
        }
    ]
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockAcquire(mock_conn)

    adapter = PgVectorStoreAdapter(pool=mock_pool)
    results = await adapter.search_similar_chunks(
        kb_id=uuid4(),
        query_embedding=[0.1] * 768,
        top_k=2,
        document_ids=[doc_id],
    )

    assert len(results) == 1
    assert results[0]["id"] == "p-1-c1"
    assert results[0]["score"] == 0.94
    assert results[0]["metadata"] == {"tag": "test"}
    assert results[0]["parent_content"] == "# Section\nFull parent content here."
