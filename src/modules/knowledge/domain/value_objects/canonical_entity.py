from pydantic import Field

from src.kernel.domain.value_object import ValueObject


class CanonicalEntity(ValueObject):
    id: str
    name: str
    entity_type: str
    aliases: list[str] = Field(default_factory=list)
