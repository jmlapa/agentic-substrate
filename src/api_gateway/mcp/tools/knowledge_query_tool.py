from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from mcp.server.mcpserver import MCPServer

from src.api_gateway.container import AppContainer
from src.kernel.domain.result import Err
from src.modules.knowledge.application.use_cases.query_knowledge import (
    QueryKnowledgeRequest,
)


@dataclass(frozen=True)
class KnowledgeQueryTool:
    container: AppContainer | Callable[[], AppContainer]

    @property
    def _container(self) -> AppContainer:
        if isinstance(self.container, AppContainer):
            return self.container
        if callable(self.container):
            return self.container()
        return self.container

    @property
    def name(self) -> str:
        return "knowledge_query"

    @property
    def description(self) -> str:
        return (
            "Consulta o grafo de conhecimento (GraphRAG) para responder perguntas complexas "
            "com síntese fact-dense e citações de fontes documentais."
        )

    async def execute(
        self,
        kb_id: str,
        query: str,
        include_graph_evidence: bool = False,
    ) -> str:
        try:
            parsed_kb_id = UUID(kb_id)
        except ValueError:
            return f"Erro: kb_id inválido: '{kb_id}'. Deve ser um UUID válido."

        use_case = self._container.query_knowledge_use_case
        request = QueryKnowledgeRequest(
            kb_id=parsed_kb_id,
            query=query,
            include_graph_triples=include_graph_evidence,
        )
        res = await use_case.execute(request)
        if isinstance(res, Err):
            return f"Erro ao consultar base de conhecimento: {res.error.message}"

        answer = res.value.answer
        if include_graph_evidence:
            evidences: list[str] = []
            if res.value.matched_entities_in_query:
                evidences.append(
                    f"- **Entidades detectadas**: {', '.join(res.value.matched_entities_in_query)}"
                )
            all_triples: list[str] = []
            for item in res.value.results:
                all_triples.extend(item.related_triples)
            if all_triples:
                unique_triples = list(dict.fromkeys(all_triples))[:10]
                evidences.append("- **Relações no Grafo (Triplas)**:")
                for trip in unique_triples:
                    evidences.append(f"  - {trip}")
            if evidences:
                answer += "\n\n### Evidências do Grafo\n" + "\n".join(evidences)
        return answer

    def register(self, server: MCPServer) -> None:
        server.tool(name=self.name, description=self.description)(self.execute)
