import tempfile
from uuid import uuid4

import pytest

from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.parent_graph_checkpoint_storage import (
    ParentGraphCheckpointStorage,
)


@pytest.mark.asyncio
async def test_parent_graph_checkpoint_storage_save_and_get() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        checkpoint_storage = ParentGraphCheckpointStorage(storage=storage)

        doc_id = uuid4()
        partition = "kb-123"
        parent_id = "parent-chunk-1"

        # Check initially false
        assert not await checkpoint_storage.has_parent(partition, doc_id, parent_id)
        assert await checkpoint_storage.get_parent(partition, doc_id, parent_id) is None

        sample_graph = ExtractedGraph(
            nodes=[
                GraphNode(
                    id="Service:Payment",
                    node_type="Service",
                    properties={"name": "Payment"},
                )
            ],
            edges=[
                GraphEdge(
                    source_id="Service:Payment",
                    target_id="Database:Postgres",
                    relationship_type="CONNECTS_TO",
                    properties={},
                )
            ],
        )

        # Save graph for parent
        await checkpoint_storage.save_parent(partition, doc_id, parent_id, sample_graph)
        assert await checkpoint_storage.has_parent(partition, doc_id, parent_id)

        loaded = await checkpoint_storage.get_parent(partition, doc_id, parent_id)
        assert loaded is not None
        assert len(loaded.nodes) == 1
        assert loaded.nodes[0].id == "Service:Payment"
        assert loaded.nodes[0].node_type == "Service"
        assert len(loaded.edges) == 1
        assert loaded.edges[0].relationship_type == "CONNECTS_TO"
