from uuid import UUID

from pydantic import BaseModel, Field


class GetDocumentContentRequest(BaseModel):
    kb_id: UUID = Field(..., description="Identificador da Knowledge Base")
    document_id: UUID = Field(..., description="Identificador único do Documento")
