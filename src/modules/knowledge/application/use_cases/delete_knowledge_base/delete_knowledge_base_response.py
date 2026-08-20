from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeleteKnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    kb_id: UUID
    success: bool
    message: str
