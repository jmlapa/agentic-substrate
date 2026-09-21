from pydantic import BaseModel, Field

from src.api_gateway.dtos.mcp_tool_parameter_dto import McpToolParameterDTO


class McpToolInfoDTO(BaseModel):
    name: str = Field(..., description="Nome identificador da ferramenta MCP")
    description: str = Field(..., description="Descrição da funcionalidade da ferramenta")
    category: str = Field(
        ...,
        description="Categoria funcional (ex: GraphRAG, Discovery, Fast-Path)",
    )
    parameters: list[McpToolParameterDTO] = Field(
        default_factory=list, description="Lista de parâmetros aceitos pela ferramenta"
    )
