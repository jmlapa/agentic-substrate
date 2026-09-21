from uuid import UUID

from pydantic import BaseModel, Field


class SyncDataSourceResponseDTO(BaseModel):
    data_source_id: UUID
    sync_run_id: UUID
    total_items_discovered: int
    status: str
    message: str = Field(default="Sincronização iniciada com sucesso. Ingestão em andamento.")
