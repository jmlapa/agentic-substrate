from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    aggregate_id: UUID
    aggregate_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__
