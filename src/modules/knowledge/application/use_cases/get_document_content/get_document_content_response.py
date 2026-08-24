from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.knowledge.application.use_cases.get_document_content.document_toc_item_dto import (
    DocumentTocItemDTO,
)


class GetDocumentContentResponse(BaseModel):
    document_id: UUID = Field(..., description="ID único do Documento")
    kb_id: UUID = Field(..., description="ID da Knowledge Base")
    file_name: str = Field(..., description="Nome original do arquivo")
    source_type: str = Field(..., description="Tipo de origem ('document', 'image', 'audio')")
    status: str = Field(..., description="Status de processamento atual")
    total_parents: int = Field(default=0, description="Total de Parent Chunks")
    total_children: int = Field(default=0, description="Total de Child Chunks")
    markdown_content: str = Field(..., description="Conteúdo textual em Markdown canônico")
    toc_tree: list[DocumentTocItemDTO] = Field(
        default_factory=list, description="Hierarquia de seções do documento"
    )
    ingested_at: float | None = Field(default=None, description="Timestamp UTC epoch de ingestão")
