from uuid import UUID

from pydantic import BaseModel, Field


class GetOntologyTemplateRequest(BaseModel):
    id: UUID | None = Field(default=None, description="ID do template")
    name: str | None = Field(default=None, description="Nome do template")
    version: int | None = Field(default=None, description="Versão do template")
