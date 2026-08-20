from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeleteDocumentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID
    success: bool
    message: str
