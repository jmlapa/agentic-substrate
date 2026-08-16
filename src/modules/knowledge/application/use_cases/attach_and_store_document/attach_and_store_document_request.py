from uuid import UUID

from pydantic import BaseModel


class AttachAndStoreDocumentRequest(BaseModel):
    kb_id: UUID
    file_name: str
    content_type: str
    file_content: bytes
