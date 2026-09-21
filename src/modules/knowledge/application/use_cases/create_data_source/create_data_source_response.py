from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CreateDataSourceResponse(BaseModel):
    id: UUID
    kb_id: UUID
    name: str
    data_source_type: str
    status: str
    sync_interval_minutes: int
    config: dict[str, Any]
    created_at: datetime
