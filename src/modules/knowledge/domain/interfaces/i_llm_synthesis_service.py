from typing import Protocol, runtime_checkable

from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)


@runtime_checkable
class ILlmSynthesisService(Protocol):
    async def synthesize_answer(
        self,
        query: str,
        search_results: list[HybridSearchResult],
    ) -> str: ...
