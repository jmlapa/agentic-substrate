from uuid import UUID

from pydantic import BaseModel, Field


class QuickSearchResultItemDTO(BaseModel):
    document_id: UUID = Field(..., description="ID do Documento correspondente")
    document_name: str = Field(..., description="Nome do Documento")
    match_type: str = Field(
        ..., description="Tipo de correspondência ('title', 'header', 'content')"
    )
    matched_title: str = Field(..., description="Título ou Seção encontrada")
    anchor: str = Field(..., description="Slug âncora para navegação direta")
    preview: str = Field(default="", description="Trecho de pré-visualização do conteúdo")
