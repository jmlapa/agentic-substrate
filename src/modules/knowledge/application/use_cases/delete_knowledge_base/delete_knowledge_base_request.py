from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeleteKnowledgeBaseRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    kb_id: UUID
