from pydantic import BaseModel, Field

from src.modules.knowledge.application.use_cases.get_ontology_template.get_ontology_template_response import (  # noqa: E501
    GetOntologyTemplateResponse,
)


class ListOntologyTemplatesResponse(BaseModel):
    templates: list[GetOntologyTemplateResponse] = Field(
        default_factory=list, description="Lista de templates de ontologia"
    )
