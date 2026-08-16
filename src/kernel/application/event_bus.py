from typing import Any, Protocol, runtime_checkable

from src.kernel.domain.domain_event import DomainEvent


@runtime_checkable
class EventBus(Protocol):
    async def publish(self, events: list[DomainEvent]) -> None: ...

    def subscribe(self, event_type: type[DomainEvent], handler: Any) -> None: ...
