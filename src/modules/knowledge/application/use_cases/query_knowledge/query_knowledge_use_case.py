from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Ok, Result
from src.modules.knowledge.application.use_cases.query_knowledge.query_knowledge_request import (
    QueryKnowledgeRequest,
)
from src.modules.knowledge.application.use_cases.query_knowledge.query_knowledge_response import (
    QueryKnowledgeResponse,
)
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore


class QueryKnowledgeUseCase:
    def __init__(self, graph_store: IGraphStore) -> None:
        self._graph_store = graph_store

    async def execute(
        self, request: QueryKnowledgeRequest
    ) -> Result[QueryKnowledgeResponse, DomainError]:
        results = await self._graph_store.query_subgraph(
            request.kb_id, request.query, request.top_k
        )
        return Ok(QueryKnowledgeResponse(nodes=results))
