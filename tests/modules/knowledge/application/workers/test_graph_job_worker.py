from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.infrastructure.atomic_job_barrier import AtomicJobBarrier
from src.modules.knowledge.application.workers.graph_job_worker import GraphJobWorker
from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate
from src.modules.knowledge.domain.interfaces.i_document_repository import (
    IDocumentRepository,
)
from src.modules.knowledge.domain.interfaces.i_graph_extractor import IGraphExtractor
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.domain.interfaces.i_stream_job_queue import IStreamJobQueue
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.domain.value_objects.job_task import JobTask
from src.modules.knowledge.infrastructure.adapters.parent_graph_checkpoint_storage import (
    ParentGraphCheckpointStorage,
)


@pytest.mark.asyncio
async def test_graph_worker_reuses_existing_checkpoint() -> None:
    mock_queue = MagicMock(spec=IStreamJobQueue)
    mock_queue.ack_task = AsyncMock(return_value=True)

    mock_storage = MagicMock(spec=IObjectStorage)
    mock_storage.exists = AsyncMock(return_value=True)  # Checkpoint exists

    checkpoint_storage = ParentGraphCheckpointStorage(storage=mock_storage)
    mock_barrier = MagicMock(spec=AtomicJobBarrier)
    mock_barrier.increment_and_check = AsyncMock(return_value=False)  # Not last

    extractor_mock = MagicMock(spec=IGraphExtractor)
    extractor_mock.extract_graph = AsyncMock()

    store_mock = MagicMock(spec=IGraphStore)
    repo_mock = MagicMock(spec=IDocumentRepository)

    worker = GraphJobWorker(
        stream_queue=mock_queue,
        storage=mock_storage,
        checkpoint_storage=checkpoint_storage,
        barrier=mock_barrier,
        graph_extractor=extractor_mock,
        graph_store=store_mock,
        document_repo=repo_mock,
    )

    doc_id = uuid4()
    kb_id = uuid4()
    task = JobTask(
        id="task-g1",
        queue_name="stream:jobs:graph",
        payload={
            "kb_id": str(kb_id),
            "document_id": str(doc_id),
            "storage_partition": f"kb-{kb_id}",
            "parent_id": "p1",
            "parent_index": 0,
            "total_parents": 2,
            "header_path": "# Section 1",
            "content": "Some text",
        },
    )

    success = await worker.process_task("msg-g1", task)
    assert success is True

    # Zero LLM extraction calls ($0.00 token cost!)
    extractor_mock.extract_graph.assert_not_called()
    mock_barrier.increment_and_check.assert_awaited_once_with(doc_id, step="graph")
    mock_queue.ack_task.assert_awaited_once_with("stream:jobs:graph", "graph_workers", "msg-g1")


@pytest.mark.asyncio
async def test_graph_worker_extracts_and_consolidates_on_last_chunk() -> None:
    mock_queue = MagicMock(spec=IStreamJobQueue)
    mock_queue.ack_task = AsyncMock(return_value=True)

    subgraph_parent_0 = ExtractedGraph(
        nodes=[GraphNode(id="n1", node_type="Technology", properties={"name": "Postgres"})],
        edges=[],
    )
    subgraph_parent_1 = ExtractedGraph(
        nodes=[GraphNode(id="n2", node_type="Technology", properties={"name": "Redis"})],
        edges=[
            GraphEdge(
                source_id="n1",
                target_id="n2",
                relationship_type="COMMUNICATES_WITH",
            )
        ],
    )

    storage_data: dict[str, bytes] = {}
    mock_storage = MagicMock(spec=IObjectStorage)

    async def mock_exists(path: str) -> bool:
        return path in storage_data

    async def mock_get(path: str) -> bytes:
        return storage_data.get(path, b"")

    async def mock_put(path: str, data: bytes, mime: str) -> None:
        storage_data[path] = data

    mock_storage.exists = AsyncMock(side_effect=mock_exists)
    mock_storage.get_object = AsyncMock(side_effect=mock_get)
    mock_storage.put_object = AsyncMock(side_effect=mock_put)

    checkpoint_storage = ParentGraphCheckpointStorage(storage=mock_storage)

    doc_id = uuid4()
    kb_id = uuid4()

    # Pre-populate parent 0 in checkpoint
    await checkpoint_storage.save_parent(
        kb_partition=f"kb-{kb_id}",
        doc_id=doc_id,
        parent_id=f"{doc_id}_parent_0",
        graph=subgraph_parent_0,
    )

    mock_barrier = MagicMock(spec=AtomicJobBarrier)
    mock_barrier.increment_and_check = AsyncMock(return_value=True)  # IS LAST!

    extractor_mock = MagicMock(spec=IGraphExtractor)
    extractor_mock.extract_graph = AsyncMock(return_value=subgraph_parent_1)

    store_mock = MagicMock(spec=IGraphStore)
    store_mock.store_graph = AsyncMock(return_value=(2, 1))

    doc = DocumentAggregate.create(
        document_id=doc_id,
        kb_id=kb_id,
        file_name="doc.pdf",
        content_type="application/pdf",
        storage_path="path.pdf",
    )
    repo_mock = MagicMock(spec=IDocumentRepository)
    repo_mock.get_by_id = AsyncMock(return_value=doc)
    repo_mock.save = AsyncMock()

    worker = GraphJobWorker(
        stream_queue=mock_queue,
        storage=mock_storage,
        checkpoint_storage=checkpoint_storage,
        barrier=mock_barrier,
        graph_extractor=extractor_mock,
        graph_store=store_mock,
        document_repo=repo_mock,
    )

    task = JobTask(
        id="task-g2",
        queue_name="stream:jobs:graph",
        payload={
            "kb_id": str(kb_id),
            "document_id": str(doc_id),
            "storage_partition": f"kb-{kb_id}",
            "parent_id": f"{doc_id}_parent_1",
            "parent_index": 1,
            "total_parents": 2,
            "header_path": "# Section 2",
            "content": "Redis is used for caching.",
        },
    )

    success = await worker.process_task("msg-g2", task)
    assert success is True

    # Verified consolidation
    store_mock.store_graph.assert_awaited_once()
    repo_mock.save.assert_awaited_once()
    assert doc.indexed_nodes_count == 2
    assert doc.indexed_edges_count == 1
    mock_queue.ack_task.assert_awaited_once_with("stream:jobs:graph", "graph_workers", "msg-g2")
