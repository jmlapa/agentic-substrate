from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    queue_name: str
    payload: dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = Field(default_factory=lambda: 0.0)
