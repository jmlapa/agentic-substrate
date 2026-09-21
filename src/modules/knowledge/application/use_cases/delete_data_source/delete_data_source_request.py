from uuid import UUID

from pydantic import BaseModel, Field


class DeleteDataSourceRequest(BaseModel):
    data_source_id: UUID = Field(..., description="ID do DataSource a ser removido")
    kb_id: UUID | None = Field(
        default=None, description="ID da Knowledge Base para validação de escopo"
    )
