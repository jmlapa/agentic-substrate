from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api_gateway.controllers.data_source_controller import (
    get_container,
    router,
)
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.create_data_source import (
    CreateDataSourceResponse,
)
from src.modules.knowledge.application.use_cases.delete_data_source import (
    DeleteDataSourceResponse,
)
from src.modules.knowledge.application.use_cases.list_data_source_runs import (
    DataSourceRunItemDTO,
    ListDataSourceRunsResponse,
)
from src.modules.knowledge.application.use_cases.list_data_sources import (
    DataSourceItemDTO,
    ListDataSourcesResponse,
)
from src.modules.knowledge.application.use_cases.sync_data_source import (
    SyncDataSourceResponse,
)


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.create_data_source_use_case = MagicMock()
    container.list_data_sources_use_case = MagicMock()
    container.list_data_source_runs_use_case = MagicMock()
    container.delete_data_source_use_case = MagicMock()
    container.sync_data_source_use_case = MagicMock()
    return container


@pytest.fixture
def client(mock_container: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: mock_container
    return TestClient(app)


def test_create_data_source_success(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    ds_id = uuid4()
    now = datetime.now(UTC)

    mock_container.create_data_source_use_case.execute = AsyncMock(
        return_value=Ok(
            CreateDataSourceResponse(
                id=ds_id,
                kb_id=kb_id,
                name="Engineering Drive",
                data_source_type="GOOGLE_DRIVE_FOLDER",
                status="IDLE",
                sync_interval_minutes=30,
                config={"folder_id": "drive-folder-123"},
                created_at=now,
            )
        )
    )

    payload = {
        "name": "Engineering Drive",
        "data_source_type": "GOOGLE_DRIVE_FOLDER",
        "config": {"folder_id": "drive-folder-123"},
        "sync_interval_minutes": 30,
    }

    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/data-sources", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == str(ds_id)
    assert data["kb_id"] == str(kb_id)
    assert data["name"] == "Engineering Drive"
    assert data["data_source_type"] == "GOOGLE_DRIVE_FOLDER"
    assert data["status"] == "IDLE"
    assert data["sync_interval_minutes"] == 30
    assert data["config"] == {"folder_id": "drive-folder-123"}


def test_create_data_source_kb_not_found(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    mock_container.create_data_source_use_case.execute = AsyncMock(
        return_value=Err(
            DomainError(f"KnowledgeBase '{kb_id}' não encontrada.", "KNOWLEDGE_BASE_NOT_FOUND")
        )
    )

    payload = {
        "name": "Docs",
        "data_source_type": "GOOGLE_DRIVE_FOLDER",
        "config": {"folder_id": "folder-1"},
    }
    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/data-sources", json=payload)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "KNOWLEDGE_BASE_NOT_FOUND"


def test_create_data_source_conflict_already_exists(
    client: TestClient, mock_container: MagicMock
) -> None:
    kb_id = uuid4()
    mock_container.create_data_source_use_case.execute = AsyncMock(
        return_value=Err(
            DomainError("Já existe um DataSource com este nome.", "DATA_SOURCE_ALREADY_EXISTS")
        )
    )

    payload = {
        "name": "Docs",
        "data_source_type": "GOOGLE_DRIVE_FOLDER",
        "config": {"folder_id": "folder-1"},
    }
    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/data-sources", json=payload)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_ALREADY_EXISTS"


def test_list_data_sources_success(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    ds_id = uuid4()
    now = datetime.now(UTC)

    mock_container.list_data_sources_use_case.execute = AsyncMock(
        return_value=Ok(
            ListDataSourcesResponse(
                data_sources=[
                    DataSourceItemDTO(
                        id=ds_id,
                        kb_id=kb_id,
                        name="Design Docs",
                        data_source_type="GOOGLE_DRIVE_FOLDER",
                        status="IDLE",
                        cursor=None,
                        sync_interval_minutes=15,
                        last_synced_at=None,
                        error_message=None,
                        config={"folder_id": "design-1"},
                        created_at=now,
                        updated_at=now,
                    )
                ]
            )
        )
    )

    resp = client.get(f"/api/v1/knowledge-bases/{kb_id}/data-sources")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(ds_id)
    assert data[0]["name"] == "Design Docs"


def test_list_data_sources_kb_not_found(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    mock_container.list_data_sources_use_case.execute = AsyncMock(
        return_value=Err(
            DomainError(f"KnowledgeBase '{kb_id}' não encontrada.", "KNOWLEDGE_BASE_NOT_FOUND")
        )
    )

    resp = client.get(f"/api/v1/knowledge-bases/{kb_id}/data-sources")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "KNOWLEDGE_BASE_NOT_FOUND"


def test_delete_data_source_success(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    ds_id = uuid4()

    mock_container.delete_data_source_use_case.execute = AsyncMock(
        return_value=Ok(
            DeleteDataSourceResponse(
                data_source_id=ds_id,
                success=True,
            )
        )
    )

    resp = client.delete(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_source_id"] == str(ds_id)
    assert data["success"] is True


def test_delete_data_source_not_found(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    ds_id = uuid4()

    mock_container.delete_data_source_use_case.execute = AsyncMock(
        return_value=Err(
            DomainError(f"DataSource '{ds_id}' não encontrado.", "DATA_SOURCE_NOT_FOUND")
        )
    )

    resp = client.delete(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_NOT_FOUND"


def test_sync_data_source_accepted(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    ds_id = uuid4()
    run_id = uuid4()

    mock_container.sync_data_source_use_case.execute = AsyncMock(
        return_value=Ok(
            SyncDataSourceResponse(
                data_source_id=ds_id,
                sync_run_id=run_id,
                total_items_discovered=12,
                status="INGESTING",
            )
        )
    )

    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/sync")
    assert resp.status_code == 202
    data = resp.json()
    assert data["data_source_id"] == str(ds_id)
    assert data["sync_run_id"] == str(run_id)
    assert data["total_items_discovered"] == 12
    assert data["status"] == "INGESTING"
    assert "Sincronização iniciada com sucesso" in data["message"]


def test_sync_data_source_already_syncing_conflict(
    client: TestClient, mock_container: MagicMock
) -> None:
    kb_id = uuid4()
    ds_id = uuid4()

    mock_container.sync_data_source_use_case.execute = AsyncMock(
        return_value=Err(
            DomainError(
                f"DataSource '{ds_id}' já está em sincronização.",
                "DATA_SOURCE_ALREADY_SYNCING",
            )
        )
    )

    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/sync")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_ALREADY_SYNCING"


def test_sync_data_source_disabled_bad_request(
    client: TestClient, mock_container: MagicMock
) -> None:
    kb_id = uuid4()
    ds_id = uuid4()

    mock_container.sync_data_source_use_case.execute = AsyncMock(
        return_value=Err(
            DomainError(f"DataSource '{ds_id}' está desativado.", "DATA_SOURCE_DISABLED")
        )
    )

    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/sync")
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_DISABLED"


def test_sync_data_source_not_found(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    ds_id = uuid4()

    mock_container.sync_data_source_use_case.execute = AsyncMock(
        return_value=Err(
            DomainError(f"DataSource '{ds_id}' não encontrado.", "DATA_SOURCE_NOT_FOUND")
        )
    )

    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/sync")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_NOT_FOUND"


def test_list_data_source_runs_success(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    ds_id = uuid4()
    run_id = uuid4()
    now = datetime.now(UTC)

    mock_container.list_data_source_runs_use_case.execute = AsyncMock(
        return_value=Ok(
            ListDataSourceRunsResponse(
                runs=[
                    DataSourceRunItemDTO(
                        id=run_id,
                        data_source_id=ds_id,
                        kb_id=kb_id,
                        status="COMPLETED",
                        total_files_discovered=5,
                        indexed_files_count=5,
                        failed_files_count=0,
                        failure_summary=[],
                        started_at=now,
                        completed_at=now,
                    )
                ]
            )
        )
    )

    resp = client.get(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/runs?limit=25")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(run_id)
    assert data[0]["data_source_id"] == str(ds_id)
    assert data[0]["status"] == "COMPLETED"
    assert data[0]["total_files_discovered"] == 5
    assert data[0]["indexed_files_count"] == 5
    assert data[0]["failed_files_count"] == 0


def test_list_data_source_runs_ds_not_found(client: TestClient, mock_container: MagicMock) -> None:
    kb_id = uuid4()
    ds_id = uuid4()

    mock_container.list_data_source_runs_use_case.execute = AsyncMock(
        return_value=Err(
            DomainError(f"DataSource '{ds_id}' não encontrado.", "DATA_SOURCE_NOT_FOUND")
        )
    )

    resp = client.get(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/runs")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "DATA_SOURCE_NOT_FOUND"


def test_use_cases_not_configured_returns_500() -> None:
    empty_container = MagicMock()
    empty_container.create_data_source_use_case = None
    empty_container.list_data_sources_use_case = None
    empty_container.delete_data_source_use_case = None
    empty_container.sync_data_source_use_case = None
    empty_container.list_data_source_runs_use_case = None

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: empty_container
    client = TestClient(app)

    kb_id = uuid4()
    ds_id = uuid4()

    resp = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/data-sources",
        json={"name": "test", "data_source_type": "google_drive_folder"},
    )
    assert resp.status_code == 500

    resp = client.get(f"/api/v1/knowledge-bases/{kb_id}/data-sources")
    assert resp.status_code == 500

    resp = client.delete(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}")
    assert resp.status_code == 500

    resp = client.post(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/sync")
    assert resp.status_code == 500

    resp = client.get(f"/api/v1/knowledge-bases/{kb_id}/data-sources/{ds_id}/runs")
    assert resp.status_code == 500
