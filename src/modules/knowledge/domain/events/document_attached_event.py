from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DocumentAttachedEvent(DomainEvent):
    document_id: UUID
    file_name: str
    content_type: str
    storage_path: str
    enable_ocr: bool = False
    ocr_instructions: str | None = None
