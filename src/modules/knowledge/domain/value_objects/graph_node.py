from typing import Any

from pydantic import Field

from src.kernel.domain.value_object import ValueObject


class GraphNode(ValueObject):
    id: str
    node_type: str
    properties: dict[str, Any] = Field(default_factory=dict)
