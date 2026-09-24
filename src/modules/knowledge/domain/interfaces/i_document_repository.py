from typing import Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate


@runtime_checkable
class IDocumentRepository(Protocol):
    """
    Protocolo de persistência e recuperação do Aggregate Root DocumentAggregate.
    Opera sobre streams de eventos unitários 'doc-{document_id}' no Event Store em O(1).
    """

    async def save(self, aggregate: DocumentAggregate) -> None: ...

    async def get_by_id(self, id: UUID) -> DocumentAggregate | None: ...

    async def load(self, id: UUID) -> DocumentAggregate | None: ...

    async def delete_by_id(self, id: UUID) -> None: ...
