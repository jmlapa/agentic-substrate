from uuid import UUID

import asyncpg

from src.kernel.application.event_store import EventStore
from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate
from src.modules.knowledge.domain.interfaces.i_document_repository import (
    IDocumentRepository,
)


class PostgresDocumentRepository(IDocumentRepository):
    """
    Adaptador de persistência para o Aggregate Root DocumentAggregate.
    Opera sobre streams de eventos unitários 'doc-{document_id}' no Event Store em O(1),
    eliminando contenção de concorrência e serialização de documentos na mesma KB.
    """

    def __init__(self, event_store: EventStore, pool: asyncpg.Pool | None = None) -> None:
        self._event_store = event_store
        self._pool = pool

    async def save(self, aggregate: DocumentAggregate) -> None:
        uncommitted = aggregate.uncommitted_events
        if not uncommitted:
            return

        expected_version = aggregate.version - len(uncommitted)
        await self._event_store.append_events(
            aggregate_id=aggregate.id,
            aggregate_type="DocumentAggregate",
            events=uncommitted,
            expected_version=expected_version,
        )
        aggregate.mark_events_as_committed()

    async def get_by_id(self, id: UUID) -> DocumentAggregate | None:
        events = await self._event_store.get_events(id)
        if not events:
            return None

        doc = DocumentAggregate(id=id)
        doc.load_from_history(events)
        return doc

    async def load(self, id: UUID) -> DocumentAggregate | None:
        return await self.get_by_id(id)

    async def delete_by_id(self, id: UUID) -> None:
        doc = await self.get_by_id(id)
        if doc is not None:
            doc.delete()
            await self.save(doc)

        if self._pool is not None:
            async with self._pool.acquire() as conn:
                await conn.execute("DELETE FROM attached_documents WHERE id = $1;", id)
