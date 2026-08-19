from typing import Any

from pydantic import BaseModel, Field

from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)


class QueryKnowledgeResponse(BaseModel):
    answer: str = Field(
        default="", description="Resposta sintetizada por LLM baseada nas evidências"
    )
    results: list[HybridSearchResult] = Field(default_factory=list)
    total_tokens_estimated: int = Field(
        default=0, description="Total estimado de tokens consumidos pelo payload textual"
    )
    matched_entities_in_query: list[str] = Field(
        default_factory=list, description="Entidades detectadas na query via zero-token linking"
    )
    retrieval_trace: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados de tracking da execução de retrieval para debug",
    )
