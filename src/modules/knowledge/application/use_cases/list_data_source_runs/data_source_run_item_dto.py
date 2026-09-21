from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DataSourceRunItemDTO(BaseModel):
    id: UUID
    data_source_id: UUID
    kb_id: UUID
    status: str
    total_files_discovered: int
    indexed_files_count: int
    failed_files_count: int
    failure_summary: list[dict[str, Any]]
    started_at: datetime
    completed_at: datetime | None
