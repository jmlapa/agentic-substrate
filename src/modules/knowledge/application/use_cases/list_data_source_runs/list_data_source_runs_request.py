from uuid import UUID

from pydantic import BaseModel, Field


class ListDataSourceRunsRequest(BaseModel):
    data_source_id: UUID = Field(..., description="ID da fonte de dados")
    limit: int = Field(default=50, description="Quantidade máxima de runs retornadas")
    kb_id: UUID | None = Field(
        default=None, description="ID da Knowledge Base para validação de escopo"
    )
