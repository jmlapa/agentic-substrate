from collections.abc import Callable
from dataclasses import dataclass

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

from src.api_gateway.container import AppContainer
from src.api_gateway.mcp.providers.knowledge_mcp_tool_provider import (
    KnowledgeMcpToolProvider,
)


@dataclass
class McpServerApplication:
    """Configura e instancia a sub-aplicação MCP sobre transporte SSE com ferramentas modulares."""

    container: AppContainer | Callable[[], AppContainer]
    server_name: str = "agentic-substrate"

    def create_app(self) -> Starlette:
        server = MCPServer(self.server_name)
        knowledge_provider = KnowledgeMcpToolProvider(container=self.container)
        knowledge_provider.register_tools(server)

        # Desabilita o bloqueio estrito de host para compatibilidade com proxies reversos e testes
        security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

        return server.sse_app(
            sse_path="/sse",
            message_path="/messages/",
            transport_security=security,
        )
