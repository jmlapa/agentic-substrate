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
