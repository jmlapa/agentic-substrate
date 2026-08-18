from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReprocessDocumentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID
    status: str
    message: str
