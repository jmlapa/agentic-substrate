from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.knowledge.application.use_cases.list_data_source_runs import (
    DataSourceRunItemDTO,
)


class DataSourceRunResponseDTO(BaseModel):
    id: UUID
    data_source_id: UUID
    kb_id: UUID
    status: str
    total_files_discovered: int = 0
    indexed_files_count: int = 0
    failed_files_count: int = 0
    failure_summary: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None

    @classmethod
    def from_item_dto(cls, item: DataSourceRunItemDTO) -> "DataSourceRunResponseDTO":
        return cls(
            id=item.id,
            data_source_id=item.data_source_id,
            kb_id=item.kb_id,
            status=item.status,
            total_files_discovered=item.total_files_discovered,
            indexed_files_count=item.indexed_files_count,
            failed_files_count=item.failed_files_count,
            failure_summary=item.failure_summary,
            started_at=item.started_at,
            completed_at=item.completed_at,
        )
