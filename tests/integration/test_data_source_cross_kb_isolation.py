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
async def test_data_source_cross_kb_isolation_delete_sync_and_runs() -> None:
    test_container = create_app_container(run_in_background=False)

    mock_connector = InMemoryDataSourceConnector()
    mock_connector.add_mock_file(
        external_id="mock-file-sec",
        name="finance.txt",
        content=b"Confidential financial figures.",
        mime_type="text/plain",
        version_hash="v1_hash",
    )
    assert test_container.data_source_connector_registry is not None
    test_container.data_source_connector_registry.register(
        DataSourceType.GOOGLE_DRIVE_FOLDER, mock_connector
    )

    test_app = create_app(container=test_container)
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create KB A
        kb_a_resp = await client.post(
            "/api/v1/knowledge/bases",
            json={
                "name": "KB A (Department A)",
                "description": "Base A",
                "ontology": {
                    "name": "OntologyA",
                    "description": "Ontology A",
                    "node_types": [],
                    "relationship_types": [],
                },
            },
        )
        assert kb_a_resp.status_code == 201
        kb_a_id = kb_a_resp.json()["id"]

        # 2. Create KB B
        kb_b_resp = await client.post(
            "/api/v1/knowledge/bases",
            json={
                "name": "KB B (Department B)",
                "description": "Base B",
                "ontology": {
                    "name": "OntologyB",
                    "description": "Ontology B",
                    "node_types": [],
                    "relationship_types": [],
                },
            },
        )
        assert kb_b_resp.status_code == 201
        kb_b_id = kb_b_resp.json()["id"]

        # 3. Create a DataSource belonging to KB B
        ds_b_resp = await client.post(
            f"/api/v1/knowledge-bases/{kb_b_id}/data-sources",
            json={
                "name": "Drive Department B",
                "data_source_type": "google_drive_folder",
                "config": {"folder_id": "dept_b_folder_123"},
                "sync_interval_minutes": 15,
            },
        )
        assert ds_b_resp.status_code == 201
        ds_b_id = ds_b_resp.json()["id"]

        # 4. ATTEMPT 1: Target KB A with ds_b_id to trigger sync (Cross-KB BOLA)
        sync_cross_resp = await client.post(
            f"/api/v1/knowledge-bases/{kb_a_id}/data-sources/{ds_b_id}/sync"
        )
        # MUST fail with 404 Not Found (or 403 Forbidden) and NOT sync KB B's data source
        assert sync_cross_resp.status_code in (404, 403), (
            f"Expected 404 or 403 for cross-KB sync, got {sync_cross_resp.status_code}"
        )

        # 5. ATTEMPT 2: Target KB A with ds_b_id to list runs (Cross-KB Information Disclosure)
        runs_cross_resp = await client.get(
            f"/api/v1/knowledge-bases/{kb_a_id}/data-sources/{ds_b_id}/runs"
        )
        assert runs_cross_resp.status_code in (404, 403), (
            f"Expected 404 or 403 for cross-KB runs list, got {runs_cross_resp.status_code}"
        )

        # 6. ATTEMPT 3: Target KB A with ds_b_id to delete (Cross-KB Tampering / Deletion)
        del_cross_resp = await client.delete(
            f"/api/v1/knowledge-bases/{kb_a_id}/data-sources/{ds_b_id}"
        )
        assert del_cross_resp.status_code in (404, 403), (
            f"Expected 404 or 403 for cross-KB delete, got {del_cross_resp.status_code}"
        )

        # 7. Verify that ds_b in KB B is STILL INTACT and untouched!
        get_b_resp = await client.get(f"/api/v1/knowledge-bases/{kb_b_id}/data-sources")
        assert get_b_resp.status_code == 200
        sources_b = get_b_resp.json()
        assert len(sources_b) == 1
        assert sources_b[0]["id"] == ds_b_id
