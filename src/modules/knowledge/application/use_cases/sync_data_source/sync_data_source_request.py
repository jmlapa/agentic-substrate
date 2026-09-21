from uuid import UUID

from pydantic import BaseModel, Field


class SyncDataSourceRequest(BaseModel):
    data_source_id: UUID = Field(..., description="ID da fonte de dados a ser sincronizada")
    kb_id: UUID | None = Field(
        default=None, description="ID da Knowledge Base para validação de escopo"
    )
