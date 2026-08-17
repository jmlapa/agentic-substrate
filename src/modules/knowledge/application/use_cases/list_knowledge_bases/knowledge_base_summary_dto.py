from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeBaseSummaryDTO(BaseModel):
    id: UUID = Field(..., description="ID da Knowledge Base")
    name: str = Field(..., description="Nome da Knowledge Base")
    description: str = Field(..., description="Descrição da Knowledge Base")
    status: str = Field(..., description="Status atual da Knowledge Base")
    storage_partition: str = Field(..., description="Partição de storage isolada")
    documents_count: int = Field(..., description="Quantidade total de documentos vinculados")
