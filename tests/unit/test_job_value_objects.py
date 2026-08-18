from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.modules.knowledge.domain.value_objects.job_task import JobTask
from src.modules.knowledge.domain.value_objects.page_ocr_job_payload import (
    PageOcrJobPayload,
)
from src.modules.knowledge.domain.value_objects.parent_graph_job_payload import (
    ParentGraphJobPayload,
)


def test_page_ocr_job_payload_creation() -> None:
    doc_id = uuid4()
    kb_id = uuid4()
    payload = PageOcrJobPayload(
        kb_id=kb_id,
        document_id=doc_id,
        storage_partition="kb-123",
        raw_storage_path="kb-123/raw/doc.pdf",
        page_number=1,
        total_pages=10,
        hierarchy_hint="# Title",
        effective_prompt="Format as GFM",
    )
    assert payload.page_number == 1
    assert payload.total_pages == 10
    assert payload.hierarchy_hint == "# Title"


def test_parent_graph_job_payload_creation() -> None:
    doc_id = uuid4()
    kb_id = uuid4()
    payload = ParentGraphJobPayload(
        kb_id=kb_id,
        document_id=doc_id,
        storage_partition="kb-123",
        parent_id="parent-1",
        parent_index=0,
        total_parents=5,
        header_path="Chapter 1 > Section 2",
        content="# Section 2\nContent text here",
    )
    assert payload.parent_id == "parent-1"
    assert payload.total_parents == 5


def test_job_task_creation() -> None:
    doc_id = uuid4()
    kb_id = uuid4()
    payload = PageOcrJobPayload(
        kb_id=kb_id,
        document_id=doc_id,
        storage_partition="kb-123",
        raw_storage_path="kb-123/raw/doc.pdf",
        page_number=1,
        total_pages=10,
        hierarchy_hint=None,
        effective_prompt="Default",
    )
    task = JobTask(
        id="task-123",
        queue_name="page_ocr_queue",
        payload=payload.model_dump(),
        retry_count=0,
        max_retries=3,
    )
    assert task.id == "task-123"
    assert task.queue_name == "page_ocr_queue"
    assert task.payload["page_number"] == 1


def test_job_task_immutability() -> None:
    task = JobTask(
        id="task-123",
        queue_name="page_ocr_queue",
        payload={"key": "val"},
    )
    with pytest.raises(ValidationError):
        task.id = "new-id"
