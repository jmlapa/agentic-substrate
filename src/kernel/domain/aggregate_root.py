import re
from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent
from src.kernel.domain.entity import Entity


class AggregateRoot(Entity[UUID]):
    def __init__(self, id: UUID, version: int = 0) -> None:
        super().__init__(id)
        self._version = version
        self._uncommitted_events: list[DomainEvent] = []

    @property
    def version(self) -> int:
        return self._version

    @property
    def uncommitted_events(self) -> list[DomainEvent]:
        return list(self._uncommitted_events)

    def mark_events_as_committed(self) -> None:
        self._uncommitted_events.clear()

    def record_event(self, event: DomainEvent) -> None:
        self.apply_event(event)
        self._uncommitted_events.append(event)
        self._version += 1

    def load_from_history(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.apply_event(event)
            self._version = max(self._version, event.event_version)

    def apply_event(self, event: DomainEvent) -> None:
        handler_name = f"_apply_{self._to_snake_case(event.__class__.__name__)}"
        handler = getattr(self, handler_name, None)
        if handler and callable(handler):
            handler(event)

    @staticmethod
    def _to_snake_case(name: str) -> str:
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
