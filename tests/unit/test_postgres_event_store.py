from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.domain_event import DomainEvent
from src.kernel.infrastructure.postgres_event_store import PostgresEventStore


class SamplePostgresEvent(DomainEvent):
    title: str


class MockTransaction:
    async def __aenter__(self) -> "MockTransaction":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


class MockAcquire:
    def __init__(self, conn: Any) -> None:
        self.conn = conn

    async def __aenter__(self) -> Any:
        return self.conn

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


@pytest.mark.asyncio
async def test_postgres_event_store_implements_protocol() -> None:
    pool = MagicMock()
    store = PostgresEventStore(pool=pool)
    assert isinstance(store, EventStore)


@pytest.mark.asyncio
async def test_postgres_event_store_initialize_schema() -> None:
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockAcquire(mock_conn)

    store = PostgresEventStore(pool=mock_pool)
    await store.initialize_schema()

    mock_conn.execute.assert_called_once()
    assert "CREATE TABLE IF NOT EXISTS event_streams" in mock_conn.execute.call_args[0][0]


@pytest.mark.asyncio
async def test_postgres_event_store_append_and_get_events() -> None:
    mock_conn = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=MockTransaction())
    mock_conn.fetchrow.return_value = None  # version 0

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockAcquire(mock_conn)

    mock_bus = MagicMock(spec=EventBus)
    mock_bus.publish = AsyncMock()

    store = PostgresEventStore(pool=mock_pool, event_bus=mock_bus)
    agg_id = uuid4()
    event = SamplePostgresEvent(aggregate_id=agg_id, aggregate_type="Sample", title="Test Event")

    await store.append_events(agg_id, "Sample", [event], expected_version=0)

    assert mock_conn.executemany.called
    assert mock_bus.publish.called

    # Mock get_events
    mock_conn.fetch.return_value = [
        {
            "event_type": "SamplePostgresEvent",
            "payload": event.model_dump_json(),
        }
    ]

    events = await store.get_events(agg_id)
    assert len(events) == 1
    assert isinstance(events[0], SamplePostgresEvent)
    assert events[0].title == "Test Event"


@pytest.mark.asyncio
async def test_postgres_event_store_concurrency_conflict() -> None:
    mock_conn = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=MockTransaction())
    mock_conn.fetchrow.return_value = {"version": 3}  # current version is 3

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = MockAcquire(mock_conn)

    store = PostgresEventStore(pool=mock_pool)
    agg_id = uuid4()
    event = SamplePostgresEvent(aggregate_id=agg_id, aggregate_type="Sample", title="Test Event")

    with pytest.raises(DomainError) as exc_info:
        await store.append_events(agg_id, "Sample", [event], expected_version=1)

    assert exc_info.value.code == "CONCURRENCY_ERROR"


@pytest.mark.asyncio
async def test_postgres_event_store_append_empty_events_noop() -> None:
    mock_pool = MagicMock()
    store = PostgresEventStore(pool=mock_pool)
    await store.append_events(UUID("00000000-0000-0000-0000-000000000000"), "Sample", [], 0)
    assert not mock_pool.acquire.called
