import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from src.kernel.application.event_bus import EventBus
from src.kernel.domain.domain_event import DomainEvent

EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, events: list[DomainEvent]) -> None:
        for event in events:
            handlers = self._handlers.get(event.__class__, [])
            if handlers:
                await asyncio.gather(*(handler(event) for handler in handlers))
