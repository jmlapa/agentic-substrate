from typing import Protocol, runtime_checkable

from mcp.server.mcpserver import MCPServer


@runtime_checkable
class IMcpToolProvider(Protocol):
    """Protocolo base para provedores modulares de ferramentas MCP."""

    def register_tools(self, server: MCPServer) -> None:
        """Registra as ferramentas do domínio na instância do MCPServer."""
        ...
