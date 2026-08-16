from typing import Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)


@runtime_checkable
class IKnowledgeBaseRepository(Protocol):
    async def save(self, aggregate: KnowledgeBaseAggregate) -> None: ...

    async def get_by_id(self, id: UUID) -> KnowledgeBaseAggregate | None: ...
