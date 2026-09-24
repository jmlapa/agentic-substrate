from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent
from src.modules.knowledge.domain.value_objects.document_source_type import (
    DocumentSourceType,
)


class DocumentAttachedEvent(DomainEvent):
    document_id: UUID
    file_name: str
    content_type: str
    storage_path: str
    kb_id: UUID | None = None
    source_type: DocumentSourceType = DocumentSourceType.DOCUMENT
    ingested_at: float = 0.0
    enable_ocr: bool = False
    ocr_instructions: str | None = None
