from fastapi import APIRouter, Depends, Request

from src.api_gateway.container import AppContainer
from src.api_gateway.dtos.mcp_info_response_dto import McpInfoResponseDTO
from src.api_gateway.dtos.mcp_tool_info_dto import McpToolInfoDTO
from src.api_gateway.dtos.mcp_tool_parameter_dto import McpToolParameterDTO

router = APIRouter(prefix="/api/v1/mcp", tags=["Model Context Protocol"])


def get_container(request: Request) -> AppContainer:
    if hasattr(request.app.state, "container") and request.app.state.container:
        return request.app.state.container  # type: ignore[no-any-return]
    from src.api_gateway.main import container

    return container


@router.get("/info", response_model=McpInfoResponseDTO)
async def get_mcp_info(
    _container: AppContainer = Depends(get_container),
) -> McpInfoResponseDTO:
    """Retorna metadados de status e ferramentas disponíveis no servidor MCP do Substrate."""
    tools = [
        McpToolInfoDTO(
            name="knowledge_query",
            description=(
                "Consulta o grafo de conhecimento (GraphRAG) para responder perguntas complexas "
                "com síntese fact-dense e citações de fontes documentais."
            ),
            category="GraphRAG",
            parameters=[
                McpToolParameterDTO(
                    name="kb_id",
                    type="string",
                    required=True,
                    description="UUID identificador da Base de Conhecimento a consultar.",
                ),
                McpToolParameterDTO(
                    name="query",
                    type="string",
                    required=True,
                    description="Pergunta ou consulta em linguagem natural a ser respondida.",
                ),
                McpToolParameterDTO(
                    name="include_graph_evidence",
                    type="boolean",
                    required=False,
                    description=(
                        "Se True, anexa as triplas ontológicas e "
                        "entidades relacionadas na resposta."
                    ),
                ),
            ],
        ),
        McpToolInfoDTO(
            name="knowledge_list_kbs",
            description=(
                "Lista todas as bases de conhecimento (Knowledge Bases) registradas no Substrate, "
                "incluindo id, nome, descrição, status e total de documentos vinculados."
            ),
            category="Discovery",
            parameters=[],
        ),
        McpToolInfoDTO(
            name="knowledge_search_notes",
            description=(
                "Busca rápida por palavras-chave, títulos e trechos em uma Base de Conhecimento "
                "(fast-path direto, sem consumo de tokens com LLM)."
            ),
            category="Fast-Path",
            parameters=[
                McpToolParameterDTO(
                    name="kb_id",
                    type="string",
                    required=True,
                    description="UUID identificador da Base de Conhecimento a pesquisar.",
                ),
                McpToolParameterDTO(
                    name="query",
                    type="string",
                    required=True,
                    description="Termo, palavra-chave ou título de seção procurado.",
                ),
                McpToolParameterDTO(
                    name="limit",
                    type="integer",
                    required=False,
                    description="Quantidade máxima de resultados a retornar (1 a 50, padrão 10).",
                ),
            ],
        ),
    ]

    return McpInfoResponseDTO(
        status="online",
        version="0.8.0",
        transport="sse",
        sse_endpoint="/mcp/sse",
        messages_endpoint="/mcp/messages",
        tools=tools,
    )
