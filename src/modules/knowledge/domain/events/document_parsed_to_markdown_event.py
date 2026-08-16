from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DocumentParsedToMarkdownEvent(DomainEvent):
    document_id: UUID
    markdown_storage_path: str
    markdown_preview: str
