from typing import Any
from unittest.mock import MagicMock

import pytest
from mcp.server.mcpserver import MCPServer

from src.api_gateway.mcp.protocols import IMcpToolProvider
from src.api_gateway.mcp.providers import KnowledgeMcpToolProvider


@pytest.fixture
def mock_container() -> Any:
    container = MagicMock()
    container.query_knowledge_use_case = MagicMock()
    container.list_kbs_use_case = MagicMock()
    container.quick_search_notes_use_case = MagicMock()
    return container


def test_knowledge_provider_implements_protocol(mock_container: Any) -> None:
    provider = KnowledgeMcpToolProvider(container=mock_container)
    assert isinstance(provider, IMcpToolProvider)


@pytest.mark.asyncio
async def test_knowledge_provider_registers_tools(mock_container: Any) -> None:
    provider = KnowledgeMcpToolProvider(container=mock_container)
    server = MCPServer("test_server")

    provider.register_tools(server)

    tools = await server.list_tools()
    registered_names = {t.name for t in tools}

    assert "knowledge_query" in registered_names
    assert "knowledge_list_kbs" in registered_names
    assert "knowledge_search_notes" in registered_names
