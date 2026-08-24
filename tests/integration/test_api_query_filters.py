import pytest
from httpx import ASGITransport, AsyncClient

from src.api_gateway.container import create_app_container
from src.api_gateway.main import create_app


@pytest.mark.asyncio
async def test_api_query_knowledge_with_filters() -> None:
    test_container = create_app_container(run_in_background=False)
    test_app = create_app(container=test_container)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create ontology
        ontology_payload = {
            "name": "FilteredKB_Ontology",
            "description": "Ontologia de teste",
            "node_types": [
                {
                    "name": "Service",
                    "description": "Serviço",
                    "properties": [{"name": "name", "type": "string", "required": True}],
                }
            ],
            "relationship_types": [],
            "version": 1,
        }
        ont_resp = await client.post("/api/v1/ontologies", json=ontology_payload)
        ont_id = ont_resp.json()["id"]

        # Create KB
        kb_resp = await client.post(
            "/api/v1/knowledge/bases",
            json={
                "name": "FilteredKB",
                "description": "KB para teste de filtros",
                "ontology_id": ont_id,
            },
        )
        kb_id = kb_resp.json()["id"]

        # Upload Doc
        doc_files = {
            "file": (
                "guide.md",
                b"# Architecture Guide\nService auth handles tokens.",
                "text/markdown",
            )
        }
        await client.post(f"/api/v1/knowledge/bases/{kb_id}/documents", files=doc_files)

        # Query with filters
        query_payload = {
            "query": "Service auth",
            "top_k": 5,
            "mode": "retrieve",
            "source_types": ["document"],
            "time_from": 1000000.0,
            "time_to": 3000000000.0,
        }
        q_resp = await client.post(f"/api/v1/knowledge/bases/{kb_id}/query", json=query_payload)
        assert q_resp.status_code == 200
        data = q_resp.json()
        assert "retrieval_trace" in data
        assert data["retrieval_trace"]["source_types"] == ["document"]
        assert data["retrieval_trace"]["time_from"] == 1000000.0
        assert data["retrieval_trace"]["time_to"] == 3000000000.0
        assert len(data["results"]) >= 1
        assert data["results"][0]["source_type"] == "document"
