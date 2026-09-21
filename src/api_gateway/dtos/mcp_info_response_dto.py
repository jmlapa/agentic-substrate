from pydantic import BaseModel, Field

from src.api_gateway.dtos.mcp_tool_info_dto import McpToolInfoDTO


class McpInfoResponseDTO(BaseModel):
    status: str = Field(default="online", description="Status de integridade do servidor MCP")
    version: str = Field(..., description="Versão atual do Substrate MCP")
    transport: str = Field(default="sse", description="Protocolo de transporte (ex: sse)")
    sse_endpoint: str = Field(default="/mcp/sse", description="Caminho relativo para conexão SSE")
    messages_endpoint: str = Field(
        default="/mcp/messages",
        description="Caminho relativo para mensagens JSON-RPC",
    )
    tools: list[McpToolInfoDTO] = Field(
        default_factory=list,
        description="Lista de ferramentas disponíveis",
    )
