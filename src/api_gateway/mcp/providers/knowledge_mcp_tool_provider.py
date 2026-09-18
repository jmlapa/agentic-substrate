from collections.abc import Callable
from dataclasses import dataclass, field

from mcp.server.mcpserver import MCPServer

from src.api_gateway.container import AppContainer
from src.api_gateway.mcp.protocols.i_mcp_tool_provider import IMcpToolProvider
from src.api_gateway.mcp.tools import (
    KnowledgeListKbsTool,
    KnowledgeQueryTool,
    KnowledgeSearchNotesTool,
)


@dataclass
class KnowledgeMcpToolProvider(IMcpToolProvider):
    """Provedor modular responsável por expor e registrar as ferramentas do módulo Knowledge."""

    container: AppContainer | Callable[[], AppContainer]
    query_tool: KnowledgeQueryTool = field(init=False)
    list_kbs_tool: KnowledgeListKbsTool = field(init=False)
    search_notes_tool: KnowledgeSearchNotesTool = field(init=False)

    def __post_init__(self) -> None:
        self.query_tool = KnowledgeQueryTool(container=self.container)
        self.list_kbs_tool = KnowledgeListKbsTool(container=self.container)
        self.search_notes_tool = KnowledgeSearchNotesTool(container=self.container)

    def register_tools(self, server: MCPServer) -> None:
        """Registra as ferramentas de consulta e busca no servidor MCP."""
        self.query_tool.register(server)
        self.list_kbs_tool.register(server)
        self.search_notes_tool.register(server)
