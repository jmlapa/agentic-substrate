from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.knowledge.domain.ontology.node_type_definition import NodeTypeDefinition
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)


class CreateOntologyTemplateResponse(BaseModel):
    id: UUID = Field(..., description="ID da ontologia criada")
    name: str
    version: int
    description: str
    node_types: list[NodeTypeDefinition]
    relationship_types: list[RelationshipTypeDefinition]
