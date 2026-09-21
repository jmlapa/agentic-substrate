from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.value_objects.data_source_run_status import (
    DataSourceRunStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_status import (
    DataSourceStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_repository import (
    InMemoryDataSourceRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_run_repository import (
    InMemoryDataSourceRunRepository,
)
from src.modules.knowledge.infrastructure.adapters.postgres_data_source_repository import (
    PostgresDataSourceRepository,
)
from src.modules.knowledge.infrastructure.adapters.postgres_data_source_run_repository import (
    PostgresDataSourceRunRepository,
)


@pytest.mark.asyncio
async def test_in_memory_data_source_repository() -> None:
    repo = InMemoryDataSourceRepository()
    kb_id = uuid4()

    ds1 = DataSource(kb_id=kb_id, name="DS 1")
    ds2 = DataSource(kb_id=kb_id, name="DS 2")
    ds_other = DataSource(kb_id=uuid4(), name="Other")

    await repo.save(ds1)
    await repo.save(ds2)
    await repo.save(ds_other)

    fetched = await repo.get_by_id(ds1.id)
    assert fetched is not None
    assert fetched.id == ds1.id

    kb_list = await repo.list_by_kb_id(kb_id)
    assert len(kb_list) == 2
    assert {d.name for d in kb_list} == {"DS 1", "DS 2"}

    assert await repo.delete(ds1.id) is True
    assert await repo.get_by_id(ds1.id) is None
    assert await repo.delete(uuid4()) is False


@pytest.mark.asyncio
async def test_in_memory_data_source_run_repository() -> None:
    repo = InMemoryDataSourceRunRepository()
    ds_id = uuid4()
    kb_id = uuid4()

    run1 = DataSourceRun(data_source_id=ds_id, kb_id=kb_id)
    run2 = DataSourceRun(data_source_id=ds_id, kb_id=kb_id)

    await repo.save(run1)
    await repo.save(run2)

    fetched = await repo.get_by_id(run1.id)
    assert fetched is not None
    assert fetched.id == run1.id

    runs = await repo.list_by_data_source_id(ds_id, limit=10)
    assert len(runs) == 2


@pytest.mark.asyncio
async def test_postgres_data_source_repository_save_and_get() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    repo = PostgresDataSourceRepository(pool=mock_pool)
    ds_id = uuid4()
    kb_id = uuid4()
    now = datetime.now(UTC)

    ds = DataSource(
        id=ds_id,
        kb_id=kb_id,
        name="Pastas do Drive",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "f_123"},
    )
    await repo.save(ds)
    assert mock_conn.execute.called

    # Mock fetchrow para get_by_id
    mock_conn.fetchrow.return_value = {
        "id": ds_id,
        "kb_id": kb_id,
        "name": "Pastas do Drive",
        "data_source_type": "google_drive_folder",
        "status": "IDLE",
        "cursor": "c_123",
        "sync_interval_minutes": 15,
        "last_synced_at": now,
        "error_message": None,
        "config": '{"folder_id": "f_123"}',
        "created_at": now,
        "updated_at": now,
    }

    fetched = await repo.get_by_id(ds_id)
    assert fetched is not None
    assert fetched.id == ds_id
    assert fetched.data_source_type == DataSourceType.GOOGLE_DRIVE_FOLDER
    assert fetched.status == DataSourceStatus.IDLE
    assert fetched.config == {"folder_id": "f_123"}


@pytest.mark.asyncio
async def test_postgres_data_source_run_repository_save_and_get() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    repo = PostgresDataSourceRunRepository(pool=mock_pool)
    run_id = uuid4()
    ds_id = uuid4()
    kb_id = uuid4()
    now = datetime.now(UTC)

    run = DataSourceRun(
        id=run_id,
        data_source_id=ds_id,
        kb_id=kb_id,
        status=DataSourceRunStatus.INGESTING,
        total_files_discovered=5,
    )
    await repo.save(run)
    assert mock_conn.execute.called

    mock_conn.fetchrow.return_value = {
        "id": run_id,
        "data_source_id": ds_id,
        "kb_id": kb_id,
        "status": "INGESTING",
        "total_files_discovered": 5,
        "indexed_files_count": 3,
        "failed_files_count": 0,
        "failure_summary": "[]",
        "started_at": now,
        "completed_at": None,
    }

    fetched = await repo.get_by_id(run_id)
    assert fetched is not None
    assert fetched.id == run_id
    assert fetched.status == DataSourceRunStatus.INGESTING
    assert fetched.total_files_discovered == 5
