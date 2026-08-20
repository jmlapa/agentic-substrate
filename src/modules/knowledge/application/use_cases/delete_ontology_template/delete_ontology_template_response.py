from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeleteOntologyTemplateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    ontology_id: UUID
    success: bool
    message: str
