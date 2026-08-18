from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReprocessDocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    kb_id: UUID
    document_id: UUID
