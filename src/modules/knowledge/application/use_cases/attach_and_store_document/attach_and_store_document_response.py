from uuid import UUID

from pydantic import BaseModel


class AttachAndStoreDocumentResponse(BaseModel):
    document_id: UUID
    storage_path: str
    status: str
