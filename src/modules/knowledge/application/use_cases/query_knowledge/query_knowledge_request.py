from uuid import UUID

from pydantic import BaseModel, Field


class QueryKnowledgeRequest(BaseModel):
    kb_id: UUID
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
