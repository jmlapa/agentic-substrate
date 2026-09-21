import pytest
from httpx import ASGITransport, AsyncClient

from src.api_gateway.container import create_app_container
from src.api_gateway.main import create_app
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_connector import (
    InMemoryDataSourceConnector,
)


@pytest.mark.asyncio
async def test_data_source_api_gateway_crud_and_sync_flow() -> None:
    test_container = create_app_container(run_in_background=False)

    # Register an in-memory mock connector for Google Drive to avoid external calls in tests
    mock_connector = InMemoryDataSourceConnector()
    mock_connector.add_mock_file(
        external_id="mock-drive-file-01",
        name="onboarding_guide.txt",
        content=b"Welcome to the engineering team. Follow strict SDD practices.",
        mime_type="text/plain",
        version_hash="v1_hash_initial",
    )
    assert test_container.data_source_connector_registry is not None
    test_container.data_source_connector_registry.register(
        DataSourceType.GOOGLE_DRIVE_FOLDER, mock_connector
    )

    test_app = create_app(container=test_container)
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Knowledge Base first
        kb_resp = await client.post(
            "/api/v1/knowledge/bases",
            json={
                "name": "Integration KB",
                "description": "Base for testing data sources",
                "ontology": {
                    "name": "IntegrationOntology",
                    "description": "Ontology for testing",
                    "node_types": [
                        {
                            "name": "Document",
                            "description": "Doc",
                            "properties": [{"name": "title", "type": "string", "required": True}],
                        }
                    ],
                    "relationship_types": [],
                },
            },
        )
        assert kb_resp.status_code == 201
        kb_id = kb_resp.json()["id"]

        # 2. POST /api/v1/knowledge-bases/{kb_id}/data-sources (Create)
        create_ds_resp = await client.post(
            f"/api/v1/knowledge-bases/{kb_id}/data-sources",
            json={
                "name": "Google Drive Engineering",
                "data_source_type": "google_drive_folder",
                "config": {"folder_id": "folder_abc_123"},
                "sync_interval_minutes": 15,
            },
        )
        assert create_ds_resp.status_code == 201
        ds_data = create_ds_resp.json()
        ds_id = ds_data["id"]
        assert ds_data["name"] == "Google Drive Engineering"
        assert ds_data["data_source_type"] == "google_drive_folder"
        assert ds_data["status"] == "IDLE"
        assert ds_data["sync_interval_minutes"] == 15
        assert ds_data["config"]["folder_id"] == "folder_abc_123"

        # 3. GET /api/v1/knowledge-bases/{kb_id}/data-sources (List)
        list_ds_resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}/data-sources")
        assert list_ds_resp.status_code == 200
        sources = list_ds_resp.json()
        assert len(sources) == 1
        assert sources[0]["id"] == ds_id
        assert sources[0]["name"] == "Google Drive Engineering"

        # 4. POST /api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/sync (Trigger sync)
        sync_resp = await client.post(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/sync")
        assert sync_resp.status_code == 202
        sync_data = sync_resp.json()
        assert sync_data["data_source_id"] == ds_id
        assert "sync_run_id" in sync_data
        run_id = sync_data["sync_run_id"]
        assert sync_data["total_items_discovered"] == 1
        assert sync_data["status"] in ("INGESTING", "COMPLETED")
        assert "Sincronização iniciada com sucesso" in sync_data["message"]

        # 5. GET /api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/runs (List runs)
        runs_resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/runs")
        assert runs_resp.status_code == 200
        runs_data = runs_resp.json()
        assert len(runs_data) == 1
        assert runs_data[0]["id"] == run_id
        assert runs_data[0]["data_source_id"] == ds_id
        assert runs_data[0]["total_files_discovered"] == 1

        # 6. DELETE /api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id} (Delete)
        del_resp = await client.delete(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}")
        assert del_resp.status_code == 200
        del_data = del_resp.json()
        assert del_data["data_source_id"] == ds_id
        assert del_data["success"] is True

        # 7. Verify list is now empty
        empty_list_resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}/data-sources")
        assert empty_list_resp.status_code == 200
        assert len(empty_list_resp.json()) == 0
