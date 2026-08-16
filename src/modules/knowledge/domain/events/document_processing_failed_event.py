from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DocumentProcessingFailedEvent(DomainEvent):
    document_id: UUID
    step: str
    error_message: str
