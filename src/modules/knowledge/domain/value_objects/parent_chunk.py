from typing import Any

from pydantic import Field

from src.kernel.domain.value_object import ValueObject


class ParentChunk(ValueObject):
    id: str
    header_path: str
    content: str
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
