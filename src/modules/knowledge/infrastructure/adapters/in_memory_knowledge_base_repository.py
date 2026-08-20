from uuid import UUID

from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)


class InMemoryKnowledgeBaseRepository(IKnowledgeBaseRepository):
    def __init__(self) -> None:
        self._kbs: dict[UUID, KnowledgeBaseAggregate] = {}

    async def save(self, aggregate: KnowledgeBaseAggregate) -> None:
        self._kbs[aggregate.id] = aggregate

    async def get_by_id(self, id: UUID) -> KnowledgeBaseAggregate | None:
        return self._kbs.get(id)

    async def list_all(self) -> list[KnowledgeBaseAggregate]:
        return list(self._kbs.values())

    async def delete_by_id(self, id: UUID) -> None:
        self._kbs.pop(id, None)

    async def delete_document(self, kb_id: UUID, document_id: UUID) -> None:
        if kb_id in self._kbs:
            self._kbs[kb_id].documents.pop(document_id, None)
