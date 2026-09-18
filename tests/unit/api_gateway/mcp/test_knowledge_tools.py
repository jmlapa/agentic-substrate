from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from mcp.server.mcpserver import MCPServer

from src.api_gateway.container import AppContainer
from src.api_gateway.mcp.tools import (
    KnowledgeListKbsTool,
    KnowledgeQueryTool,
    KnowledgeSearchNotesTool,
)
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.list_knowledge_bases.knowledge_base_summary_dto import (  # noqa: E501
    KnowledgeBaseSummaryDTO,
)
from src.modules.knowledge.application.use_cases.list_knowledge_bases.list_knowledge_bases_response import (  # noqa: E501
    ListKnowledgeBasesResponse,
)
from src.modules.knowledge.application.use_cases.query_knowledge.query_knowledge_response import (
    QueryKnowledgeResponse,
)
from src.modules.knowledge.application.use_cases.quick_search_notes.quick_search_notes_response import (  # noqa: E501
    QuickSearchNotesResponse,
)
from src.modules.knowledge.application.use_cases.quick_search_notes.quick_search_result_item_dto import (  # noqa: E501
    QuickSearchResultItemDTO,
)


@pytest.fixture
def mock_container() -> Any:
    container = MagicMock(spec=AppContainer)
    container.query_knowledge_use_case = MagicMock()
    container.list_kbs_use_case = MagicMock()
    container.quick_search_notes_use_case = MagicMock()
    return container


@pytest.mark.asyncio
async def test_knowledge_query_tool_invalid_uuid(mock_container: Any) -> None:
    tool = KnowledgeQueryTool(container=mock_container)
    result = await tool.execute(kb_id="invalid-uuid", query="O que é X?")
    assert "Erro: kb_id inválido" in result


@pytest.mark.asyncio
async def test_knowledge_query_tool_success(mock_container: Any) -> None:
    kb_id = uuid4()
    mock_container.query_knowledge_use_case.execute = AsyncMock(
        return_value=Ok(
            QueryKnowledgeResponse(
                answer="Resposta sintetizada com fatos.",
                results=[],
            )
        )
    )
    tool = KnowledgeQueryTool(container=mock_container)
    result = await tool.execute(kb_id=str(kb_id), query="O que é X?")
    assert "Resposta sintetizada com fatos." in result
    assert "### Evidências do Grafo" not in result


@pytest.mark.asyncio
async def test_knowledge_query_tool_with_subgraph_evidence(
    mock_container: Any,
) -> None:
    kb_id = uuid4()
    mock_container.query_knowledge_use_case.execute = AsyncMock(
        return_value=Ok(
            QueryKnowledgeResponse(
                answer="Resposta com grafo.",
                results=[],
                matched_entities_in_query=["Agentic Substrate", "FalkorDB"],
            )
        )
    )
    tool = KnowledgeQueryTool(container=mock_container)
    result = await tool.execute(kb_id=str(kb_id), query="O que é X?", include_graph_evidence=True)
    assert "Resposta com grafo." in result
    assert "### Evidências do Grafo" in result
    assert "Agentic Substrate" in result


@pytest.mark.asyncio
async def test_knowledge_query_tool_error(mock_container: Any) -> None:
    kb_id = uuid4()
    mock_container.query_knowledge_use_case.execute = AsyncMock(
        return_value=Err(DomainError(code="KB_NOT_FOUND", message="Base inexistente"))
    )
    tool = KnowledgeQueryTool(container=mock_container)
    result = await tool.execute(kb_id=str(kb_id), query="O que é X?")
    assert "Erro ao consultar base de conhecimento: Base inexistente" in result


@pytest.mark.asyncio
async def test_knowledge_list_kbs_tool_empty(mock_container: Any) -> None:
    mock_container.list_kbs_use_case.execute = AsyncMock(
        return_value=Ok(ListKnowledgeBasesResponse(knowledge_bases=[]))
    )
    tool = KnowledgeListKbsTool(container=mock_container)
    result = await tool.execute()
    assert "Nenhuma base de conhecimento encontrada" in result


@pytest.mark.asyncio
async def test_knowledge_list_kbs_tool_populated(mock_container: Any) -> None:
    kb_id = uuid4()
    mock_container.list_kbs_use_case.execute = AsyncMock(
        return_value=Ok(
            ListKnowledgeBasesResponse(
                knowledge_bases=[
                    KnowledgeBaseSummaryDTO(
                        id=kb_id,
                        name="Base Financeira",
                        description="Documentos de balanço",
                        status="READY",
                        storage_partition="kb_fin",
                        documents_count=5,
                    )
                ]
            )
        )
    )
    tool = KnowledgeListKbsTool(container=mock_container)
    result = await tool.execute()
    assert "Base Financeira" in result
    assert str(kb_id) in result
    assert "Documentos: 5" in result


@pytest.mark.asyncio
async def test_knowledge_search_notes_tool_success(mock_container: Any) -> None:
    kb_id = uuid4()
    doc_id = uuid4()
    mock_container.quick_search_notes_use_case.execute = AsyncMock(
        return_value=Ok(
            QuickSearchNotesResponse(
                query="lucro",
                results=[
                    QuickSearchResultItemDTO(
                        document_id=doc_id,
                        document_name="relatorio_anual.md",
                        match_type="header",
                        matched_title="Lucro Líquido 2025",
                        anchor="lucro-liquido-2025",
                        preview="O lucro líquido no ano foi...",
                    )
                ],
            )
        )
    )
    tool = KnowledgeSearchNotesTool(container=mock_container)
    result = await tool.execute(kb_id=str(kb_id), query="lucro")
    assert "Resultados da busca rápida para 'lucro'" in result
    assert "relatorio_anual.md" in result
    assert "Lucro Líquido 2025" in result
    assert str(doc_id) in result


@pytest.mark.asyncio
async def test_knowledge_tools_register_on_mcpserver(mock_container: Any) -> None:
    server = MCPServer("test_server")
    query_tool = KnowledgeQueryTool(container=mock_container)
    list_tool = KnowledgeListKbsTool(container=mock_container)
    search_tool = KnowledgeSearchNotesTool(container=mock_container)

    query_tool.register(server)
    list_tool.register(server)
    search_tool.register(server)

    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "knowledge_query" in tool_names
    assert "knowledge_list_kbs" in tool_names
    assert "knowledge_search_notes" in tool_names
