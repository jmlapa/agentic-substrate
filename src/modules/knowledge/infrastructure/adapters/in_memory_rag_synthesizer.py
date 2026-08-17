from src.modules.knowledge.domain.interfaces.i_llm_synthesis_service import (
    ILlmSynthesisService,
)
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)


class InMemoryRagSynthesizer(ILlmSynthesisService):
    def __init__(self, prefix: str = "Resposta sintetizada:") -> None:
        self._prefix = prefix

    async def synthesize_answer(
        self,
        query: str,
        search_results: list[HybridSearchResult],
    ) -> str:
        if not search_results:
            return (
                "Nenhum documento ou contexto relevante foi encontrado na Knowledge Base "
                "para responder a essa pergunta."
            )

        contexts: list[str] = []
        for r in search_results:
            if r.parent_content:
                header = f" [{r.header_path}]" if r.header_path else ""
                contexts.append(f"- ({r.parent_chunk_id}{header}): {r.parent_content[:200]}")

        context_summary = "\n".join(contexts) if contexts else "Sem conteúdo textual direto."
        return (
            f"{self._prefix} Com base nas evidências recuperadas para '{query}', "
            f"temos:\n\n{context_summary}"
        )
