import json
from typing import Any
from uuid import UUID

import asyncpg

from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.domain_event import DomainEvent


class PostgresEventStore(EventStore):
    def __init__(
        self,
        pool: asyncpg.Pool,
        event_bus: EventBus | None = None,
    ) -> None:
        self._pool = pool
        self._event_bus = event_bus
        self._event_types: dict[str, type[DomainEvent]] = {}
        self._register_known_subclasses(DomainEvent)

    def _register_known_subclasses(self, cls: type[DomainEvent]) -> None:
        for sub in cls.__subclasses__():
            self._event_types[sub.__name__] = sub
            self._register_known_subclasses(sub)

    def register_event_type(self, event_type: type[DomainEvent]) -> None:
        self._event_types[event_type.__name__] = event_type

    async def initialize_schema(self) -> None:
        query = """
        CREATE TABLE IF NOT EXISTS event_streams (
            aggregate_id UUID PRIMARY KEY,
            aggregate_type VARCHAR(255) NOT NULL,
            version INT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS domain_events (
            event_id UUID PRIMARY KEY,
            aggregate_id UUID NOT NULL,
            aggregate_type VARCHAR(255) NOT NULL,
            event_type VARCHAR(255) NOT NULL,
            event_version INT NOT NULL,
            payload JSONB NOT NULL,
            occurred_at TIMESTAMPTZ NOT NULL,
            metadata JSONB NOT NULL,
            UNIQUE (aggregate_id, event_version)
        );

        CREATE INDEX IF NOT EXISTS idx_domain_events_aggregate_id 
        ON domain_events (aggregate_id, event_version ASC);
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query)

    async def append_events(
        self,
        aggregate_id: UUID,
        aggregate_type: str,
        events: list[DomainEvent],
        expected_version: int,
    ) -> None:
        if not events:
            return

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT version FROM event_streams WHERE aggregate_id = $1 FOR UPDATE",
                    aggregate_id,
                )
                current_version = int(row["version"]) if row else 0

                if current_version != expected_version:
                    raise DomainError(
                        f"Concurrency conflict: expected version {expected_version}, "
                        f"got {current_version}",
                        code="CONCURRENCY_ERROR",
                    )

                new_version = current_version + len(events)
                await conn.execute(
                    """
                    INSERT INTO event_streams (aggregate_id, aggregate_type, version)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (aggregate_id) DO UPDATE SET version = $3
                    """,
                    aggregate_id,
                    aggregate_type,
                    new_version,
                )

                records: list[tuple[UUID, UUID, str, str, int, str, Any, str]] = []
                for i, event in enumerate(events, start=current_version + 1):
                    event.event_version = i
                    payload_json = event.model_dump_json()
                    metadata_json = json.dumps(event.metadata)
                    records.append(
                        (
                            event.event_id,
                            aggregate_id,
                            aggregate_type,
                            event.event_type,
                            event.event_version,
                            payload_json,
                            event.occurred_at,
                            metadata_json,
                        )
                    )

                await conn.executemany(
                    """
                    INSERT INTO domain_events (
                        event_id, aggregate_id, aggregate_type, event_type,
                        event_version, payload, occurred_at, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8::jsonb)
                    """,
                    records,
                )

        if self._event_bus:
            await self._event_bus.publish(events)

    async def get_events(self, aggregate_id: UUID) -> list[DomainEvent]:
        # Refresh subclasses if new events were loaded dynamically
        self._register_known_subclasses(DomainEvent)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_type, payload
                FROM domain_events
                WHERE aggregate_id = $1
                ORDER BY event_version ASC
                """,
                aggregate_id,
            )

        events: list[DomainEvent] = []
        for row in rows:
            event_type_str: str = row["event_type"]
            payload_str: str = row["payload"]
            cls = self._event_types.get(event_type_str, DomainEvent)
            event_obj = cls.model_validate_json(payload_str)
            events.append(event_obj)
        return events
