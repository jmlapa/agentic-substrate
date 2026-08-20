from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DocumentDeletedEvent(DomainEvent):
    document_id: UUID
