from pydantic import BaseModel, Field


class QueryKnowledgeDTO(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
