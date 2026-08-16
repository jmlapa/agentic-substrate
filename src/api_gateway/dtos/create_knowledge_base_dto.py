from pydantic import BaseModel

from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema


class CreateKnowledgeBaseDTO(BaseModel):
    name: str
    description: str
    ontology: OntologySchema
