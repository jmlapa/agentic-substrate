from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema


class CreateKnowledgeBaseRequest(BaseModel):
    name: str = Field(..., description="Nome da Base de Conhecimento")
    description: str = Field(..., description="Descrição da Base de Conhecimento")
    ontology_id: UUID | None = Field(
        default=None, description="ID do template de ontologia pré-existente"
    )
    ontology: OntologySchema | None = Field(
        default=None,
        description="Schema de ontologia inline (opcional se ontology_id for informado)",
    )
