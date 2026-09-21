from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.domain.domain_event import DomainEvent
from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.create_data_source import (
    CreateDataSourceRequest,
    CreateDataSourceUseCase,
)
from src.modules.knowledge.application.use_cases.delete_data_source import (
    DeleteDataSourceRequest,
    DeleteDataSourceUseCase,
)
from src.modules.knowledge.application.use_cases.list_data_source_runs import (
    ListDataSourceRunsRequest,
    ListDataSourceRunsUseCase,
)
from src.modules.knowledge.application.use_cases.list_data_sources import (
    ListDataSourcesRequest,
    ListDataSourcesUseCase,
)
from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.events.data_source_created_event import (
    DataSourceCreatedEvent,
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


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    async def publish(self, events: list[DomainEvent]) -> None:
        self.published.extend(events)

    def subscribe(self, event_type: Any, handler: Any) -> None:
        pass


@pytest.mark.asyncio
async def test_create_data_source_success() -> None:
    kb_repo = MagicMock()
    fake_kb = MagicMock()
    kb_repo.get_by_id = AsyncMock(return_value=fake_kb)

    ds_repo = InMemoryDataSourceRepository()
    event_bus = DummyEventBus()

    use_case = CreateDataSourceUseCase(
        kb_repository=kb_repo,
        data_source_repository=ds_repo,
        event_bus=event_bus,
    )

    kb_id = uuid4()
    req = CreateDataSourceRequest(
        kb_id=kb_id,
        name="Drive Documents",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "root-123", "baseline_days": 15},
        sync_interval_minutes=30,
    )

    result = await use_case.execute(req)
    assert isinstance(result, Ok)
    res = result.value
    assert res.kb_id == kb_id
    assert res.name == "Drive Documents"
    assert res.data_source_type == "google_drive_folder"
    assert res.sync_interval_minutes == 30
    assert res.config["folder_id"] == "root-123"

    saved = await ds_repo.get_by_id(res.id)
    assert saved is not None
    assert saved.name == "Drive Documents"

    assert len(event_bus.published) == 1
    event = event_bus.published[0]
    assert isinstance(event, DataSourceCreatedEvent)
    assert event.name == "Drive Documents"


@pytest.mark.asyncio
async def test_create_data_source_kb_not_found() -> None:
    kb_repo = MagicMock()
    kb_repo.get_by_id = AsyncMock(return_value=None)
    ds_repo = InMemoryDataSourceRepository()

    use_case = CreateDataSourceUseCase(
        kb_repository=kb_repo,
        data_source_repository=ds_repo,
    )

    req = CreateDataSourceRequest(
        kb_id=uuid4(),
        name="Drive",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "root-123"},
    )

    result = await use_case.execute(req)
    assert isinstance(result, Err)
    assert result.error.code == "KNOWLEDGE_BASE_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_data_source_invalid_config() -> None:
    kb_repo = MagicMock()
    kb_repo.get_by_id = AsyncMock(return_value=MagicMock())
    ds_repo = InMemoryDataSourceRepository()

    use_case = CreateDataSourceUseCase(
        kb_repository=kb_repo,
        data_source_repository=ds_repo,
    )

    req = CreateDataSourceRequest(
        kb_id=uuid4(),
        name="Drive",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={},  # Missing folder_id
    )

    result = await use_case.execute(req)
    assert isinstance(result, Err)
    assert result.error.code == "INVALID_DATA_SOURCE_CONFIG"


@pytest.mark.asyncio
async def test_list_data_sources() -> None:
    ds_repo = InMemoryDataSourceRepository()
    use_case = ListDataSourcesUseCase(data_source_repository=ds_repo)

    kb_id = uuid4()
    other_kb_id = uuid4()

    ds1 = DataSource(
        kb_id=kb_id,
        name="DS 1",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "f1"},
    )
    ds2 = DataSource(
        kb_id=kb_id,
        name="DS 2",
        data_source_type=DataSourceType.LOCAL_DIRECTORY,
        config={"path": "/tmp"},
    )
    ds_other = DataSource(
        kb_id=other_kb_id,
        name="DS Other",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "f_other"},
    )

    await ds_repo.save(ds1)
    await ds_repo.save(ds2)
    await ds_repo.save(ds_other)

    result = await use_case.execute(ListDataSourcesRequest(kb_id=kb_id))
    assert isinstance(result, Ok)
    assert len(result.value.data_sources) == 2
    names = [d.name for d in result.value.data_sources]
    assert "DS 1" in names
    assert "DS 2" in names
    assert "DS Other" not in names


@pytest.mark.asyncio
async def test_list_data_source_runs() -> None:
    run_repo = InMemoryDataSourceRunRepository()
    use_case = ListDataSourceRunsUseCase(run_repository=run_repo)

    ds_id = uuid4()
    kb_id = uuid4()

    run1 = DataSourceRun(data_source_id=ds_id, kb_id=kb_id)
    run2 = DataSourceRun(data_source_id=ds_id, kb_id=kb_id)
    other_run = DataSourceRun(data_source_id=uuid4(), kb_id=kb_id)

    await run_repo.save(run1)
    await run_repo.save(run2)
    await run_repo.save(other_run)

    result = await use_case.execute(ListDataSourceRunsRequest(data_source_id=ds_id, limit=10))
    assert isinstance(result, Ok)
    assert len(result.value.runs) == 2
    run_ids = [r.id for r in result.value.runs]
    assert run1.id in run_ids
    assert run2.id in run_ids
    assert other_run.id not in run_ids


@pytest.mark.asyncio
async def test_delete_data_source_success() -> None:
    ds_repo = InMemoryDataSourceRepository()
    use_case = DeleteDataSourceUseCase(data_source_repository=ds_repo)

    ds = DataSource(
        kb_id=uuid4(),
        name="To Delete",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "f1"},
    )
    await ds_repo.save(ds)

    result = await use_case.execute(DeleteDataSourceRequest(data_source_id=ds.id))
    assert isinstance(result, Ok)
    assert result.value.success is True
    assert result.value.data_source_id == ds.id

    rem = await ds_repo.get_by_id(ds.id)
    assert rem is None


@pytest.mark.asyncio
async def test_delete_data_source_not_found() -> None:
    ds_repo = InMemoryDataSourceRepository()
    use_case = DeleteDataSourceUseCase(data_source_repository=ds_repo)

    non_existent = uuid4()
    result = await use_case.execute(DeleteDataSourceRequest(data_source_id=non_existent))
    assert isinstance(result, Err)
    assert result.error.code == "DATA_SOURCE_NOT_FOUND"
