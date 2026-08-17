from uuid import uuid4

from src.modules.knowledge.domain.events.document_chunked_event import (
    DocumentChunkedEvent,
)


def test_document_chunked_event_creation() -> None:
    kb_id = uuid4()
    doc_id = uuid4()
    event = DocumentChunkedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        total_parents=3,
        total_children=8,
        chunks_summary=[
            {"parent_id": "parent-1", "header_path": "# Intro", "child_count": 2},
            {"parent_id": "parent-2", "header_path": "## Details", "child_count": 6},
        ],
    )

    assert event.aggregate_id == kb_id
    assert event.document_id == doc_id
    assert event.total_parents == 3
    assert event.total_children == 8
    assert event.event_type == "DocumentChunkedEvent"
    assert len(event.chunks_summary) == 2
