from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DocumentStoredEvent(DomainEvent):
    document_id: UUID
    storage_path: str
    byte_size: int
    kb_id: UUID | None = None
