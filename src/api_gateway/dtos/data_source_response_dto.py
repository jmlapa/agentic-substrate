from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.knowledge.application.use_cases.create_data_source import (
    CreateDataSourceResponse,
)
from src.modules.knowledge.application.use_cases.list_data_sources import (
    DataSourceItemDTO,
)


class DataSourceResponseDTO(BaseModel):
    id: UUID
    kb_id: UUID
    name: str
    data_source_type: str
    status: str
    cursor: str | None = None
    sync_interval_minutes: int = 15
    last_synced_at: datetime | None = None
    error_message: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def from_response(cls, resp: CreateDataSourceResponse) -> "DataSourceResponseDTO":
        return cls(
            id=resp.id,
            kb_id=resp.kb_id,
            name=resp.name,
            data_source_type=resp.data_source_type,
            status=resp.status,
            sync_interval_minutes=resp.sync_interval_minutes,
            config=resp.config,
            created_at=resp.created_at,
            updated_at=resp.created_at,
        )

    @classmethod
    def from_item_dto(cls, item: DataSourceItemDTO) -> "DataSourceResponseDTO":
        return cls(
            id=item.id,
            kb_id=item.kb_id,
            name=item.name,
            data_source_type=item.data_source_type,
            status=item.status,
            cursor=item.cursor,
            sync_interval_minutes=item.sync_interval_minutes,
            last_synced_at=item.last_synced_at,
            error_message=item.error_message,
            config=item.config,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
