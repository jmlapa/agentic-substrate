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


class QueryKnowledgeUseCase:
    def __init__(
        self,
        graph_store: IGraphStore,
        embedding_service: IEmbeddingService,
    ) -> None:
        self._graph_store = graph_store
        self._embedding_service = embedding_service

    async def execute(
        self, request: QueryKnowledgeRequest
    ) -> Result[QueryKnowledgeResponse, DomainError]:
        embeddings = await self._embedding_service.embed_texts([request.query])
        query_vec = embeddings[0] if embeddings else []

        results = await self._graph_store.query_hybrid(request.kb_id, query_vec, request.top_k)
        return Ok(QueryKnowledgeResponse(results=results))
