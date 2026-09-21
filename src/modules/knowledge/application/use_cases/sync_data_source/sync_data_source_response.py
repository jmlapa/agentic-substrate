from uuid import UUID

from pydantic import BaseModel


class SyncDataSourceResponse(BaseModel):
    data_source_id: UUID
    sync_run_id: UUID
    total_items_discovered: int
    status: str
