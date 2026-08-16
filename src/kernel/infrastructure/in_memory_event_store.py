from collections import defaultdict
from uuid import UUID

from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.domain_event import DomainEvent


class InMemoryEventStore(EventStore):
    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._store: dict[UUID, list[DomainEvent]] = defaultdict(list)
        self._event_bus = event_bus

    async def append_events(
        self,
        aggregate_id: UUID,
        aggregate_type: str,
        events: list[DomainEvent],
        expected_version: int,
    ) -> None:
        current_events = self._store[aggregate_id]
        current_version = len(current_events)
        if current_version != expected_version:
            raise DomainError(
                f"Concurrency conflict: expected version {expected_version}, got {current_version}",
                code="CONCURRENCY_ERROR",
            )
        for i, event in enumerate(events, start=current_version + 1):
            event.event_version = i
            self._store[aggregate_id].append(event)

        if self._event_bus:
            await self._event_bus.publish(events)

    async def get_events(self, aggregate_id: UUID) -> list[DomainEvent]:
        return list(self._store.get(aggregate_id, []))
