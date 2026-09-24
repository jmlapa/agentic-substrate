from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.infrastructure.atomic_job_barrier import AtomicJobBarrier
from src.modules.knowledge.application.workers.ocr_job_worker import OcrJobWorker
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.domain.interfaces.i_stream_job_queue import IStreamJobQueue
from src.modules.knowledge.domain.value_objects.job_task import JobTask
from src.modules.knowledge.infrastructure.adapters.page_checkpoint_storage import (
    PageCheckpointStorage,
)


@pytest.mark.asyncio
async def test_ocr_worker_reuses_existing_checkpoint() -> None:
    mock_queue = MagicMock(spec=IStreamJobQueue)
    mock_queue.ack_task = AsyncMock(return_value=True)

    mock_storage = MagicMock(spec=IObjectStorage)
    mock_storage.exists = AsyncMock(return_value=True)  # Checkpoint exists!

    checkpoint_storage = PageCheckpointStorage(storage=mock_storage)

    mock_barrier = MagicMock(spec=AtomicJobBarrier)
    mock_barrier.increment_and_check = AsyncMock(return_value=False)  # Not last

    parser_mock = AsyncMock()

    worker = OcrJobWorker(
        stream_queue=mock_queue,
        storage=mock_storage,
        checkpoint_storage=checkpoint_storage,
        barrier=mock_barrier,
        page_parser_fn=parser_mock,
    )

    doc_id = uuid4()
    kb_id = uuid4()
    task = JobTask(
        id="task-1",
        queue_name="stream:jobs:ocr",
        payload={
            "kb_id": str(kb_id),
            "document_id": str(doc_id),
            "storage_partition": f"kb-{kb_id}",
            "raw_storage_path": "path.pdf",
            "page_number": 1,
            "total_pages": 3,
        },
    )

    success = await worker.process_task("msg-1", task)
    assert success is True

    # Checkpoint was reused, so parser was NEVER called ($0.00 token cost!)
    parser_mock.assert_not_called()
    mock_barrier.increment_and_check.assert_awaited_once_with(doc_id, step="ocr")
    mock_queue.ack_task.assert_awaited_once_with("stream:jobs:ocr", "ocr_workers", "msg-1")


@pytest.mark.asyncio
async def test_ocr_worker_executes_parser_and_consolidates_on_last_chunk() -> None:
    mock_queue = MagicMock(spec=IStreamJobQueue)
    mock_queue.ack_task = AsyncMock(return_value=True)

    doc_id = uuid4()

    # In-memory storage mock
    stored_objects: dict[str, bytes] = {
        f"kb-1/ocr_cache/{doc_id}/page_0001.md": b"# Page 1 Content",
        f"kb-1/ocr_cache/{doc_id}/page_0002.md": b"# Page 2 Content",
    }

    mock_storage = MagicMock(spec=IObjectStorage)

    async def mock_exists(path: str) -> bool:
        return path in stored_objects

    async def mock_get(path: str) -> bytes:
        return stored_objects.get(path, b"")

    async def mock_put(path: str, data: bytes, mime: str) -> None:
        stored_objects[path] = data

    mock_storage.exists = AsyncMock(side_effect=mock_exists)
    mock_storage.get_object = AsyncMock(side_effect=mock_get)
    mock_storage.put_object = AsyncMock(side_effect=mock_put)

    checkpoint_storage = PageCheckpointStorage(storage=mock_storage)

    mock_barrier = MagicMock(spec=AtomicJobBarrier)
    mock_barrier.increment_and_check = AsyncMock(return_value=True)  # IS LAST!

    parser_mock = AsyncMock(return_value="# Page 2 Content")
    completed_callback = AsyncMock()

    worker = OcrJobWorker(
        stream_queue=mock_queue,
        storage=mock_storage,
        checkpoint_storage=checkpoint_storage,
        barrier=mock_barrier,
        page_parser_fn=parser_mock,
        on_completed_callback=completed_callback,
    )

    task = JobTask(
        id="task-2",
        queue_name="stream:jobs:ocr",
        payload={
            "kb_id": str(uuid4()),
            "document_id": str(doc_id),
            "storage_partition": "kb-1",
            "raw_storage_path": "path.pdf",
            "page_number": 2,
            "total_pages": 2,
        },
    )

    success = await worker.process_task("msg-2", task)
    assert success is True

    # Consolidation was triggered
    expected_full_md_path = f"kb-1/markdown/{doc_id}.md"
    assert expected_full_md_path in stored_objects
    full_text = stored_objects[expected_full_md_path].decode("utf-8")
    assert "# Page 1 Content" in full_text
    assert "# Page 2 Content" in full_text

    completed_callback.assert_awaited_once()
    mock_queue.ack_task.assert_awaited_once_with("stream:jobs:ocr", "ocr_workers", "msg-2")
