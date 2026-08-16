from pydantic import BaseModel, Field

from src.modules.knowledge.domain.ontology.property_definition import PropertyDefinition


class NodeTypeDefinition(BaseModel):
    name: str
    description: str
    properties: list[PropertyDefinition] = Field(default_factory=list)
