from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeleteOntologyTemplateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    ontology_id: UUID
