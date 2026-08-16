from pydantic import BaseModel, Field

from src.modules.knowledge.domain.ontology.node_type_definition import NodeTypeDefinition
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)


class OntologySchema(BaseModel):
    name: str
    description: str
    node_types: list[NodeTypeDefinition] = Field(default_factory=list)
    relationship_types: list[RelationshipTypeDefinition] = Field(default_factory=list)

    def get_node_type(self, name: str) -> NodeTypeDefinition | None:
        return next((nt for nt in self.node_types if nt.name == name), None)

    def get_relationship_type(self, name: str) -> RelationshipTypeDefinition | None:
        return next((rt for rt in self.relationship_types if rt.name == name), None)
