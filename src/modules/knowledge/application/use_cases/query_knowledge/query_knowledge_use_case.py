import math
from typing import Any

from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Ok, Result
from src.modules.knowledge.application.use_cases.query_knowledge.query_knowledge_request import (
    QueryKnowledgeRequest,
)
from src.modules.knowledge.application.use_cases.query_knowledge.query_knowledge_response import (
    QueryKnowledgeResponse,
)
from src.modules.knowledge.domain.interfaces.i_embedding_service import (
    IEmbeddingService,
)
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_llm_synthesis_service import (
    ILlmSynthesisService,
)
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)


class QueryKnowledgeUseCase:
    MIN_USEFUL_TOKENS = 50

    def __init__(
        self,
        graph_store: IGraphStore,
        embedding_service: IEmbeddingService,
        synthesis_service: ILlmSynthesisService | None = None,
    ) -> None:
        self._graph_store = graph_store
        self._embedding_service = embedding_service
        self._synthesis_service = synthesis_service

    def _estimate_tokens(self, text: str) -> int:
        return max(1, math.ceil(len(text) / 3.3)) if text else 0

    def _apply_token_budgeting(
        self, results: list[HybridSearchResult], max_budget: int
    ) -> tuple[list[HybridSearchResult], int, bool]:
        budgeted: list[HybridSearchResult] = []
        current_tokens = 0
        truncated = False
        suffix = "... [truncado pelo orçamento]"
        suffix_tokens = self._estimate_tokens(suffix)

        for _idx, res in enumerate(results):
            res_tokens = self._estimate_tokens(res.parent_content)
            if current_tokens + res_tokens <= max_budget:
                budgeted.append(res)
                current_tokens += res_tokens
            else:
                remaining_tokens = max_budget - current_tokens
                if _idx == 0 or remaining_tokens >= (self.MIN_USEFUL_TOKENS + suffix_tokens):
                    available_tokens = max(1, remaining_tokens - suffix_tokens)
                    max_chars = max(20, int(available_tokens * 3.3))
                    trimmed_content = res.parent_content[:max_chars].rstrip() + suffix
                    trimmed_res = HybridSearchResult(
                        parent_chunk_id=res.parent_chunk_id,
                        document_id=res.document_id,
                        document_name=res.document_name,
                        header_path=res.header_path,
                        parent_content=trimmed_content,
                        relevance_score=res.relevance_score,
                        retrieval_source=res.retrieval_source,
                        prev_chunk_id=res.prev_chunk_id,
                        next_chunk_id=res.next_chunk_id,
                        related_triples=res.related_triples,
                        related_entities=res.related_entities,
                    )
                    budgeted.append(trimmed_res)
                    current_tokens += self._estimate_tokens(trimmed_content)
                truncated = True
                break

        return budgeted, current_tokens, truncated

    async def execute(
        self, request: QueryKnowledgeRequest
    ) -> Result[QueryKnowledgeResponse, DomainError]:
        candidate_k = max(request.top_k * 4, 50)
        query_vec = await self._embedding_service.embed_query(request.query)

        raw_results = await self._graph_store.query_hybrid(
            request.kb_id, query_vec, request.top_k, candidate_k
        )

        if not raw_results:
            answer = (
                "Nenhum documento ou contexto relevante foi encontrado na Knowledge Base "
                "para responder a essa pergunta."
            )
            return Ok(
                QueryKnowledgeResponse(
                    answer=answer,
                    results=[],
                    total_tokens_estimated=0,
                    retrieval_trace={
                        "candidate_k": candidate_k,
                        "top_k": request.top_k,
                        "mode": request.mode,
                        "token_budget_limit": request.max_tokens_budget,
                        "token_budget_consumed": 0,
                        "budget_truncated": False,
                        "results_count": 0,
                    },
                )
            )

        budgeted_results, total_tokens, is_truncated = self._apply_token_budgeting(
            raw_results, request.max_tokens_budget
        )

        trace: dict[str, Any] = {
            "candidate_k": candidate_k,
            "top_k": request.top_k,
            "mode": request.mode,
            "token_budget_limit": request.max_tokens_budget,
            "token_budget_consumed": total_tokens,
            "budget_truncated": is_truncated,
            "results_count": len(budgeted_results),
            "retrieval_sources": [r.retrieval_source for r in budgeted_results],
        }

        if request.mode == "retrieve":
            count = len(budgeted_results)
            answer = f"Modo retrieve: {count} evidências recuperadas do grafo de conhecimento."
        elif self._synthesis_service is not None:
            answer = await self._synthesis_service.synthesize_answer(
                request.query, budgeted_results
            )
            if answer.startswith("Erro na comunicação com o LLM"):
                trace["synthesis_error"] = True
        else:
            count = len(budgeted_results)
            answer = f"Foram recuperadas {count} evidências do grafo de conhecimento."

        return Ok(
            QueryKnowledgeResponse(
                answer=answer,
                results=budgeted_results,
                total_tokens_estimated=total_tokens,
                retrieval_trace=trace,
            )
        )
