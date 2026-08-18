from uuid import uuid4

from src.kernel.domain.domain_event import DomainEvent
from src.modules.knowledge.domain.events.document_progress_updated_event import (
    DocumentProgressUpdatedEvent,
)


def test_document_progress_updated_event_creation() -> None:
    kb_id = uuid4()
    doc_id = uuid4()
    event = DocumentProgressUpdatedEvent(
        aggregate_id=kb_id,
        document_id=doc_id,
        step="OCR",
        current=45,
        total=437,
        percentage=10,
        message="Processando página 45 de 437",
    )
    assert isinstance(event, DomainEvent)
    assert event.aggregate_id == kb_id
    assert event.document_id == doc_id
    assert event.step == "OCR"
    assert event.current == 45
    assert event.total == 437
    assert event.percentage == 10
    assert event.message == "Processando página 45 de 437"
