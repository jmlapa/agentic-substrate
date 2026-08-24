from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.modules.knowledge.infrastructure.adapters.falkordb_graph_store_adapter import (
    FalkorDbGraphStoreAdapter,
)


@pytest.mark.asyncio
async def test_falkordb_query_hybrid_filters() -> None:
    mock_client = MagicMock()
    mock_graph = MagicMock()
    mock_client.select_graph.return_value = mock_graph

    mock_result = MagicMock()
    mock_result.result_set = [
        [
            "parent_1",
            "doc_1",
            "doc.pdf",
            "# Header",
            "Content text",
            0.95,
            None,
            None,
            True,
            "document",
            1787238000.0,
            [],
            [],
        ]
    ]
    mock_graph.query.return_value = mock_result

    adapter = FalkorDbGraphStoreAdapter(client=mock_client)
    kb_id = uuid4()

    results = await adapter.query_hybrid(
        kb_id=kb_id,
        query_embedding=[0.1, 0.2, 0.3],
        top_k=3,
        candidate_k=20,
        source_types=["document", "image"],
        time_from=1700000000.0,
        time_to=1800000000.0,
    )

    assert len(results) == 1
    assert results[0].parent_chunk_id == "parent_1"
    assert results[0].source_type == "document"
    assert results[0].ingested_at == 1787238000.0

    mock_graph.query.assert_called_once()
    call_args = mock_graph.query.call_args
    query_str = call_args[0][0]
    params = call_args[0][1]

    assert "p_seed.source_type IN $source_types" in query_str
    assert "p_seed.ingested_at >= $time_from" in query_str
    assert "p_seed.ingested_at <= $time_to" in query_str
    assert params["source_types"] == ["document", "image"]
    assert params["time_from"] == 1700000000.0
    assert params["time_to"] == 1800000000.0
