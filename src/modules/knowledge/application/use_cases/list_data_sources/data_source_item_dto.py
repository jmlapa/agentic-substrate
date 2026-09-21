from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DataSourceItemDTO(BaseModel):
    id: UUID
    kb_id: UUID
    name: str
    data_source_type: str
    status: str
    cursor: str | None
    sync_interval_minutes: int
    last_synced_at: datetime | None
    error_message: str | None
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
