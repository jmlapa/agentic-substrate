import pytest
from httpx import ASGITransport, AsyncClient

from src.api_gateway.container import create_app_container
from src.api_gateway.main import create_app


@pytest.mark.asyncio
async def test_get_mcp_info_success() -> None:
    test_container = create_app_container(run_in_background=False)
    test_app = create_app(container=test_container)
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/mcp/info")
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "online"
        assert data["version"] == "0.8.0"
        assert data["transport"] == "sse"
        assert data["sse_endpoint"] == "/mcp/sse"
        assert data["messages_endpoint"] == "/mcp/messages"

        tools = {t["name"]: t for t in data["tools"]}
        assert "knowledge_query" in tools
        assert "knowledge_list_kbs" in tools
        assert "knowledge_search_notes" in tools

        # Test knowledge_query schema
        query_tool = tools["knowledge_query"]
        assert query_tool["category"] == "GraphRAG"
        query_params = {p["name"]: p for p in query_tool["parameters"]}
        assert "kb_id" in query_params
        assert query_params["kb_id"]["required"] is True
        assert query_params["kb_id"]["type"] == "string"
        assert "query" in query_params
        assert query_params["query"]["required"] is True
        assert "include_graph_evidence" in query_params
        assert query_params["include_graph_evidence"]["required"] is False

        # Test knowledge_list_kbs schema
        list_tool = tools["knowledge_list_kbs"]
        assert list_tool["category"] == "Discovery"
        assert list_tool["parameters"] == []

        # Test knowledge_search_notes schema
        search_tool = tools["knowledge_search_notes"]
        assert search_tool["category"] == "Fast-Path"
        search_params = {p["name"]: p for p in search_tool["parameters"]}
        assert "kb_id" in search_params
        assert search_params["kb_id"]["required"] is True
        assert "query" in search_params
        assert search_params["query"]["required"] is True
        assert "limit" in search_params
        assert search_params["limit"]["required"] is False
        assert search_params["limit"]["type"] == "integer"
