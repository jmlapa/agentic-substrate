from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DocumentProgressUpdatedEvent(DomainEvent):
    aggregate_type: str = "DocumentAggregate"
    document_id: UUID
    kb_id: UUID | None = None
    step: str
    current: int
    total: int
    percentage: int
    message: str | None = None
