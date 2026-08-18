from pydantic import BaseModel, Field


class QueryKnowledgeDTO(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    mode: str = Field(
        default="synthesis",
        description="Modo de consulta: 'synthesis' (LLM fact-dense) ou 'retrieve' (fast-path)",
    )
