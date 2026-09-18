from collections.abc import Callable
from dataclasses import dataclass

from mcp.server.mcpserver import MCPServer

from src.api_gateway.container import AppContainer
from src.kernel.domain.result import Err
from src.modules.knowledge.application.use_cases.list_knowledge_bases import (
    ListKnowledgeBasesRequest,
)


@dataclass(frozen=True)
class KnowledgeListKbsTool:
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
        return "knowledge_list_kbs"

    @property
    def description(self) -> str:
        return (
            "Lista todas as bases de conhecimento (Knowledge Bases) registradas no Substrate, "
            "incluindo id, nome, descrição, status e total de documentos vinculados."
        )

    async def execute(self) -> str:
        use_case = self._container.list_kbs_use_case
        res = await use_case.execute(ListKnowledgeBasesRequest())
        if isinstance(res, Err):
            return f"Erro ao listar bases de conhecimento: {res.error.message}"

        if not res.value.knowledge_bases:
            return "Nenhuma base de conhecimento encontrada no Substrate."

        lines = ["# Bases de Conhecimento Disponíveis\n"]
        for kb in res.value.knowledge_bases:
            lines.append(
                f"- **{kb.name}** (`{kb.id}`)\n"
                f"  - Descrição: {kb.description}\n"
                f"  - Status: {kb.status}\n"
                f"  - Documentos: {kb.documents_count}"
            )
        return "\n".join(lines)

    def register(self, server: MCPServer) -> None:
        server.tool(name=self.name, description=self.description)(self.execute)
