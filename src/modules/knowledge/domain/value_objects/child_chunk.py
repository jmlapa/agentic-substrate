from typing import Any

from pydantic import Field

from src.kernel.domain.value_object import ValueObject


class ChildChunk(ValueObject):
    id: str
    parent_chunk_id: str
    chunk_index: int
    header_path: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
