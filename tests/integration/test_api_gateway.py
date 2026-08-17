import pytest
from httpx import ASGITransport, AsyncClient

from src.api_gateway.main import app


@pytest.mark.asyncio
async def test_api_e2e_flow() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

        # 2. Criar template de ontologia reutilizável
        ontology_payload = {
            "name": "E2ETestOntology",
            "description": "Ontologia de teste E2E",
            "node_types": [
                {
                    "name": "Microservice",
                    "description": "Serviço",
                    "properties": [
                        {"name": "language", "type": "string", "required": True},
                        {"name": "port", "type": "integer", "required": False, "default": 3000},
                    ],
                }
            ],
            "relationship_types": [],
            "version": 1,
        }

        create_ont_resp = await client.post("/api/v1/ontologies", json=ontology_payload)
        assert create_ont_resp.status_code == 201
        ont_data = create_ont_resp.json()
        ont_id = ont_data["id"]
        assert ont_data["name"] == "E2ETestOntology"

        # Listar templates de ontologia
        list_ont_resp = await client.get("/api/v1/ontologies")
        assert list_ont_resp.status_code == 200
        assert len(list_ont_resp.json()["templates"]) >= 1

        # Buscar template por ID
        get_ont_resp = await client.get(f"/api/v1/ontologies/{ont_id}")
        assert get_ont_resp.status_code == 200
        assert get_ont_resp.json()["id"] == ont_id

        # 3. Criar Knowledge Base vinculada via ontology_id
        create_kb_resp = await client.post(
            "/api/v1/knowledge/bases",
            json={
                "name": "E2E Knowledge Base",
                "description": "Base criada via API referenciando template",
                "ontology_id": ont_id,
            },
        )
        assert create_kb_resp.status_code == 201
        kb_data = create_kb_resp.json()
        kb_id = kb_data["id"]
        assert kb_data["name"] == "E2E Knowledge Base"
        assert "storage_partition" in kb_data

        # 4. Upload Document
        files = {
            "file": (
                "service_doc.txt",
                b"Architecture includes Microservice auth",
                "text/plain",
            )
        }
        upload_resp = await client.post(
            f"/api/v1/knowledge/bases/{kb_id}/documents",
            files=files,
        )
        assert upload_resp.status_code == 202
        upload_data = upload_resp.json()
        assert "document_id" in upload_data

        # 5. Check KB status and processed document
        get_kb_resp = await client.get(f"/api/v1/knowledge/bases/{kb_id}")
        assert get_kb_resp.status_code == 200
        kb_details = get_kb_resp.json()
        assert len(kb_details["documents"]) == 1
        assert kb_details["documents"][0]["status"] == "INDEXED"

        # List all Knowledge Bases
        list_kbs_resp = await client.get("/api/v1/knowledge/bases")
        assert list_kbs_resp.status_code == 200
        kbs_data = list_kbs_resp.json()
        assert len(kbs_data["knowledge_bases"]) >= 1
        assert any(k["id"] == kb_id for k in kbs_data["knowledge_bases"])

        # 6. Query Knowledge Base (RAG with synthesized answer)
        query_resp = await client.post(
            f"/api/v1/knowledge/bases/{kb_id}/query",
            json={"query": "Tell me about Microservice", "top_k": 3},
        )
        assert query_resp.status_code == 200
        query_data = query_resp.json()
        assert len(query_data["results"]) >= 1
        assert "answer" in query_data
        assert len(query_data["answer"]) > 0
