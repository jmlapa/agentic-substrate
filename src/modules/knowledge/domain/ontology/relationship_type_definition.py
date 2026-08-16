from pydantic import BaseModel, Field

from src.modules.knowledge.domain.ontology.property_definition import PropertyDefinition


class RelationshipTypeDefinition(BaseModel):
    name: str
    description: str
    source_node_type: str
    target_node_type: str
    properties: list[PropertyDefinition] = Field(default_factory=list)
