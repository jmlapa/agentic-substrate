from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DocumentProgressUpdatedEvent(DomainEvent):
    aggregate_type: str = "KnowledgeBaseAggregate"
    document_id: UUID
    step: str
    current: int
    total: int
    percentage: int
    message: str | None = None
