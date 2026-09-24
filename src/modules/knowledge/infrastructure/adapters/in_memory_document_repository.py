from uuid import UUID

from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate
from src.modules.knowledge.domain.interfaces.i_document_repository import (
    IDocumentRepository,
)


class InMemoryDocumentRepository(IDocumentRepository):
    """
    Repositório em memória para o Aggregate Root DocumentAggregate.
    Utilizado principalmente para testes unitários com isolamento completo de I/O.
    """

    def __init__(self) -> None:
        self._documents: dict[UUID, DocumentAggregate] = {}

    async def save(self, aggregate: DocumentAggregate) -> None:
        aggregate.mark_events_as_committed()
        self._documents[aggregate.id] = aggregate

    async def get_by_id(self, id: UUID) -> DocumentAggregate | None:
        return self._documents.get(id)

    async def load(self, id: UUID) -> DocumentAggregate | None:
        return await self.get_by_id(id)

    async def delete_by_id(self, id: UUID) -> None:
        doc = self._documents.get(id)
        if doc is not None:
            doc.delete()
        self._documents.pop(id, None)
