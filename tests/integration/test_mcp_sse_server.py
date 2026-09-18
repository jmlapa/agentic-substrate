import asyncio
import socket
from uuid import uuid4

import anyio
import pytest
import uvicorn
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.types import TextContent

from src.api_gateway.container import create_app_container
from src.api_gateway.main import create_app
from src.kernel.domain.result import Ok
from src.modules.knowledge.application.use_cases.create_knowledge_base import (
    CreateKnowledgeBaseRequest,
)
from src.modules.knowledge.application.use_cases.create_ontology_template import (
    CreateOntologyTemplateRequest,
)


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.mark.asyncio
async def test_mcp_sse_server_handshake_and_tools() -> None:
    port = _get_free_port()
    container = create_app_container(graph_store_type="in_memory", run_in_background=False)

    # 1. Cria uma ontologia base para permitir a criação da KB
    ont_res = await container.create_ontology_use_case.execute(
        CreateOntologyTemplateRequest(
            name="Ontologia MCP",
            description="Ontologia de teste para o servidor MCP",
            node_types=[],
            relationship_types=[],
            version=1,
        )
    )
    assert isinstance(ont_res, Ok)

    # 2. Cria uma Knowledge Base real no repositório em memória
    create_res = await container.create_kb_use_case.execute(
        CreateKnowledgeBaseRequest(
            name="Base de Teste MCP",
            description="Knowledge base para teste de integração do MCP",
            ontology_id=ont_res.value.id,
        )
    )
    assert isinstance(create_res, Ok)
    kb_id = str(create_res.value.id)

    app = create_app(container=container)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)

    async with anyio.create_task_group() as tg:
        tg.start_soon(uv_server.serve)
        while not uv_server.started:
            await asyncio.sleep(0.05)

        try:
            url = f"http://127.0.0.1:{port}/mcp/sse"
            async with sse_client(url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # 1. Initialize Handshake
                    init_res = await session.initialize()
                    assert init_res.server_info.name == "agentic-substrate"

                    # 2. List Tools
                    tools_res = await session.list_tools()
                    discovered_names = {t.name for t in tools_res.tools}
                    assert "knowledge_query" in discovered_names
                    assert "knowledge_list_kbs" in discovered_names
                    assert "knowledge_search_notes" in discovered_names

                    # 3. Call knowledge_list_kbs (deve listar a KB criada)
                    list_res = await session.call_tool("knowledge_list_kbs")
                    assert len(list_res.content) > 0
                    assert isinstance(list_res.content[0], TextContent)
                    assert "Base de Teste MCP" in list_res.content[0].text
                    assert kb_id in list_res.content[0].text

                    # 4. Call knowledge_search_notes na KB criada (sem documentos ainda)
                    search_res = await session.call_tool(
                        "knowledge_search_notes",
                        {"kb_id": kb_id, "query": "faturamento"},
                    )
                    assert len(search_res.content) > 0
                    assert isinstance(search_res.content[0], TextContent)
                    assert (
                        f"Nenhuma nota ou seção encontrada para a busca 'faturamento' na base '{kb_id}'."  # noqa: E501
                        in search_res.content[0].text
                    )

                    # 5. Call knowledge_query com KB inexistente
                    fake_kb_id = str(uuid4())
                    query_res = await session.call_tool(
                        "knowledge_query",
                        {"kb_id": fake_kb_id, "query": "Qual o faturamento?"},
                    )
                    assert len(query_res.content) > 0
                    assert isinstance(query_res.content[0], TextContent)

                    # 6. Call knowledge_search_notes com KB inexistente (valida erro)
                    err_search = await session.call_tool(
                        "knowledge_search_notes",
                        {"kb_id": fake_kb_id, "query": "faturamento"},
                    )
                    assert len(err_search.content) > 0
                    assert isinstance(err_search.content[0], TextContent)
                    assert "Erro ao buscar notas" in err_search.content[0].text
        finally:
            uv_server.should_exit = True
            await asyncio.sleep(0.1)
