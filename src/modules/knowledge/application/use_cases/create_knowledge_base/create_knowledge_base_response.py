from uuid import UUID

from pydantic import BaseModel


class CreateKnowledgeBaseResponse(BaseModel):
    id: UUID
    name: str
    storage_partition: str
    status: str
