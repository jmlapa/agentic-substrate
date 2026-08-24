import pytest
from httpx import ASGITransport, AsyncClient

from src.api_gateway.container import create_app_container
from src.api_gateway.main import create_app


@pytest.mark.asyncio
async def test_notes_portal_endpoints(tmp_path: pytest.TempPathFactory) -> None:
    test_container = create_app_container(
        storage_base_dir=str(tmp_path),
        run_in_background=False,
    )
    test_app = create_app(container=test_container)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 0. Criar Template de Ontologia
        ont_resp = await client.post(
            "/api/v1/ontologies",
            json={
                "name": "NotesOntology",
                "description": "Ontology for notes tests",
                "node_types": [],
                "relationship_types": [],
                "version": 1,
            },
        )
        assert ont_resp.status_code == 201
        ont_id = ont_resp.json()["id"]

        # 1. Criar Knowledge Base
        create_kb_resp = await client.post(
            "/api/v1/knowledge/bases",
            json={
                "name": "Notes Portal KB",
                "description": "Base para testes de visualização e busca rápida",
                "ontology_id": ont_id,
            },
        )
        assert create_kb_resp.status_code == 201
        kb_id = create_kb_resp.json()["id"]

        # 2. Upload de documento Markdown
        md_content = (
            "# 1. Guia do Desenvolvedor\n\n"
            "Bem-vindo ao guia.\n\n"
            "## 1.1 Configuração de Ambiente\n\n"
            "Execute `make dev` para iniciar a stack.\n\n"
            "## 1.2 Pipeline de Ingestão\n\n"
            "Explicação dos eventos."
        )
        upload_resp = await client.post(
            f"/api/v1/knowledge/bases/{kb_id}/documents",
            files={"file": ("guia_dev.md", md_content.encode("utf-8"), "text/markdown")},
        )
        assert upload_resp.status_code == 202
        doc_id = upload_resp.json()["document_id"]

        # 3. Testar GET /content
        content_resp = await client.get(
            f"/api/v1/knowledge/bases/{kb_id}/documents/{doc_id}/content"
        )
        assert content_resp.status_code == 200
        content_data = content_resp.json()
        assert content_data["document_id"] == doc_id
        assert content_data["kb_id"] == kb_id
        assert content_data["file_name"] == "guia_dev.md"
        assert content_data["status"] == "INDEXED"
        assert "Guia do Desenvolvedor" in content_data["markdown_content"]
        assert len(content_data["toc_tree"]) == 3
        assert content_data["toc_tree"][0]["title"] == "1. Guia do Desenvolvedor"
        assert content_data["toc_tree"][0]["anchor"] == "1-guia-do-desenvolvedor"
        assert content_data["toc_tree"][1]["title"] == "1.1 Configuração de Ambiente"
        assert content_data["toc_tree"][1]["anchor"] == "11-configuracao-de-ambiente"

        # 4. Testar GET /quick-search por título
        search_title_resp = await client.get(f"/api/v1/knowledge/bases/{kb_id}/quick-search?q=guia")
        assert search_title_resp.status_code == 200
        search_title_data = search_title_resp.json()
        assert search_title_data["query"] == "guia"
        assert len(search_title_data["results"]) >= 1
        assert search_title_data["results"][0]["document_name"] == "guia_dev.md"

        # 5. Testar GET /quick-search por cabeçalho
        search_header_resp = await client.get(
            f"/api/v1/knowledge/bases/{kb_id}/quick-search?q=Configuração"
        )
        assert search_header_resp.status_code == 200
        search_header_data = search_header_resp.json()
        assert len(search_header_data["results"]) >= 1

        # 6. Testar 404 para KB ou documento inexistente
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        not_found_resp = await client.get(
            f"/api/v1/knowledge/bases/{fake_uuid}/documents/{doc_id}/content"
        )
        assert not_found_resp.status_code == 404
