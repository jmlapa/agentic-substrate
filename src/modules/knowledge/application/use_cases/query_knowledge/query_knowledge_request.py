from uuid import UUID

from pydantic import BaseModel, Field


class QueryKnowledgeRequest(BaseModel):
    kb_id: UUID
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
