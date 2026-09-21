from uuid import UUID

from pydantic import BaseModel, Field


class ListDataSourcesRequest(BaseModel):
    kb_id: UUID = Field(..., description="ID da Base de Conhecimento")
