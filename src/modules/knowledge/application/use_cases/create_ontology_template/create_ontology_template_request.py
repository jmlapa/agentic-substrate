from pydantic import BaseModel, Field

from src.modules.knowledge.domain.ontology.node_type_definition import NodeTypeDefinition
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)


class CreateOntologyTemplateRequest(BaseModel):
    name: str = Field(..., description="Nome canônico da ontologia")
    description: str = Field(..., description="Descrição e escopo da ontologia")
    node_types: list[NodeTypeDefinition] = Field(default_factory=list, description="Tipos de nós")
    relationship_types: list[RelationshipTypeDefinition] = Field(
        default_factory=list, description="Tipos de relacionamentos"
    )
    version: int = Field(default=1, ge=1, description="Versão da ontologia")
