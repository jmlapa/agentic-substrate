from pydantic import BaseModel, Field

from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)


class QueryKnowledgeResponse(BaseModel):
    results: list[HybridSearchResult] = Field(default_factory=list)
