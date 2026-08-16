from uuid import UUID, uuid4

import pytest

from src.kernel.domain.aggregate_root import AggregateRoot
from src.kernel.domain.domain_event import DomainEvent
from src.kernel.domain.result import Err, Ok
from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore


class SampleCreatedEvent(DomainEvent):
    name: str


class SampleAggregate(AggregateRoot):
    def __init__(self, id: UUID | None = None) -> None:
        super().__init__(id or uuid4())
        self.name: str = ""

    def create(self, name: str) -> None:
        self.record_event(
            SampleCreatedEvent(
                aggregate_id=self.id,
                aggregate_type="SampleAggregate",
                name=name,
            )
        )

    def _apply_sample_created_event(self, event: SampleCreatedEvent) -> None:
        self.name = event.name


def test_result_types() -> None:
    ok_res = Ok(10)
    assert ok_res.is_ok()
    assert not ok_res.is_err()
    assert ok_res.value == 10

    err_res = Err("error")
    assert err_res.is_err()
    assert not err_res.is_ok()
    assert err_res.error == "error"


@pytest.mark.asyncio
async def test_aggregate_and_event_store() -> None:
    bus = InMemoryEventBus()
    store = InMemoryEventStore(event_bus=bus)

    published: list[DomainEvent] = []

    async def on_created(event: DomainEvent) -> None:
        published.append(event)

    bus.subscribe(SampleCreatedEvent, on_created)

    agg = SampleAggregate()
    agg.create("test-knowledge")
    assert len(agg.uncommitted_events) == 1
    assert agg.name == "test-knowledge"

    await store.append_events(agg.id, "SampleAggregate", agg.uncommitted_events, expected_version=0)
    agg.mark_events_as_committed()
    assert len(agg.uncommitted_events) == 0
    assert len(published) == 1

    # Load from history
    events = await store.get_events(agg.id)
    reloaded = SampleAggregate(id=agg.id)
    reloaded.load_from_history(events)
    assert reloaded.name == "test-knowledge"
    assert reloaded.version == 1
