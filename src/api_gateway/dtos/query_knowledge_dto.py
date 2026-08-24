from uuid import UUID

from pydantic import BaseModel, Field


class QueryKnowledgeDTO(BaseModel):
    query: str
    top_k: int = Field(default=20, ge=1, le=20, description="Quantidade estrita de pais a retornar")
    mode: str = Field(
        default="synthesis",
        description="Modo de consulta: 'synthesis' (LLM fact-dense) ou 'retrieve' (fast-path)",
    )
    max_tokens_budget: int = Field(
        default=32000,
        ge=50,
        le=32000,
        description="Teto máximo de tokens estimados para o payload textual",
    )
    include_graph_triples: bool = Field(
        default=True,
        description="Inclui triplas relacionais estruturadas do subgrafo",
    )
    source_types: list[str] | None = Field(
        default=None,
        description="Filtro opcional por origens universais ('document', 'image', 'audio')",
    )
    time_from: float | None = Field(
        default=None,
        description="Timestamp epoch UTC inicial para filtro temporal",
    )
    time_to: float | None = Field(
        default=None,
        description="Timestamp epoch UTC final para filtro temporal",
    )
    document_id: UUID | None = Field(
        default=None,
        description="Filtro opcional para restringir a busca ao escopo de um documento específico",
    )
