from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from mcp.server.mcpserver import MCPServer

from src.api_gateway.container import AppContainer
from src.kernel.domain.result import Err
from src.modules.knowledge.application.use_cases.quick_search_notes import (
    QuickSearchNotesRequest,
)


@dataclass(frozen=True)
class KnowledgeSearchNotesTool:
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
        return "knowledge_search_notes"

    @property
    def description(self) -> str:
        return (
            "Busca rápida por palavras-chave, títulos e trechos em uma Base de Conhecimento "
            "(fast-path direto, sem consumo de tokens com LLM)."
        )

    async def execute(self, kb_id: str, query: str, limit: int = 10) -> str:
        try:
            parsed_kb_id = UUID(kb_id)
        except ValueError:
            return f"Erro: kb_id inválido: '{kb_id}'. Deve ser um UUID válido."

        clamped_limit = max(1, min(50, limit))
        use_case = self._container.quick_search_notes_use_case
        request = QuickSearchNotesRequest(
            kb_id=parsed_kb_id,
            query=query,
            limit=clamped_limit,
        )
        res = await use_case.execute(request)
        if isinstance(res, Err):
            return f"Erro ao buscar notas: {res.error.message}"

        if not res.value.results:
            return f"Nenhuma nota ou seção encontrada para a busca '{query}' na base '{kb_id}'."

        lines = [f"# Resultados da busca rápida para '{query}'\n"]
        for item in res.value.results:
            header = f"- **{item.document_name}** | Seção: *{item.matched_title}* (`{item.match_type}`)\n"  # noqa: E501
            lines.append(
                header + f"  - Document ID: `{item.document_id}`\n  - Trecho: {item.preview}"
            )
        return "\n".join(lines)

    def register(self, server: MCPServer) -> None:
        server.tool(name=self.name, description=self.description)(self.execute)
