from typing import Any

from pydantic import Field

from src.kernel.domain.value_object import ValueObject


class HybridSearchResult(ValueObject):
    parent_chunk_id: str
    header_path: str
    parent_content: str
    relevance_score: float
    related_entities: list[dict[str, Any]] = Field(default_factory=list)
