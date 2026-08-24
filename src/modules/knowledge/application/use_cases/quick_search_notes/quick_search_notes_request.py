from uuid import UUID

from pydantic import BaseModel, Field


class QuickSearchNotesRequest(BaseModel):
    kb_id: UUID = Field(..., description="ID da Knowledge Base a ser pesquisada")
    query: str = Field(..., min_length=1, description="Termo de busca digitado pelo usuário")
    limit: int = Field(default=10, ge=1, le=50, description="Limite máximo de sugestões")
