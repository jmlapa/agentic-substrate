from typing import Protocol, runtime_checkable
from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


@runtime_checkable
class EventStore(Protocol):
    async def append_events(
        self,
        aggregate_id: UUID,
        aggregate_type: str,
        events: list[DomainEvent],
        expected_version: int,
    ) -> None: ...

    async def get_events(self, aggregate_id: UUID) -> list[DomainEvent]: ...
