from typing import Any

from pydantic import Field

from src.kernel.domain.value_object import ValueObject


class GraphEdge(ValueObject):
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, Any] = Field(default_factory=dict)
