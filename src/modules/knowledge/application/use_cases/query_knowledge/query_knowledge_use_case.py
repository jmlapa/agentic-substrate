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


class QueryKnowledgeUseCase:
    def __init__(
        self,
        graph_store: IGraphStore,
        embedding_service: IEmbeddingService,
        synthesis_service: ILlmSynthesisService | None = None,
    ) -> None:
        self._graph_store = graph_store
        self._embedding_service = embedding_service
        self._synthesis_service = synthesis_service

    async def execute(
        self, request: QueryKnowledgeRequest
    ) -> Result[QueryKnowledgeResponse, DomainError]:
        embeddings = await self._embedding_service.embed_texts([request.query])
        query_vec = embeddings[0] if embeddings else []

        results = await self._graph_store.query_hybrid(request.kb_id, query_vec, request.top_k)

        answer = ""
        if self._synthesis_service is not None:
            answer = await self._synthesis_service.synthesize_answer(request.query, results)
        elif not results:
            answer = (
                "Nenhum documento ou contexto relevante foi encontrado na Knowledge Base "
                "para responder a essa pergunta."
            )
        else:
            answer = f"Foram recuperadas {len(results)} evidências do grafo de conhecimento."

        return Ok(QueryKnowledgeResponse(answer=answer, results=results))
