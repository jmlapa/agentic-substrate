from typing import Any

from pydantic import BaseModel

from src.modules.knowledge.domain.ontology.property_type import PropertyType


class PropertyDefinition(BaseModel):
    name: str
    type: PropertyType
    description: str | None = None
    required: bool = True
    default: Any | None = None
    enum_values: list[str] | None = None
