from typing import Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.value_objects.canonical_entity import (
    CanonicalEntity,
)


@runtime_checkable
class IEntityRegistry(Protocol):
    """
    Contrato abstrato para consulta e registro cumulativo de entidades canônicas por Knowledge Base.
    """

    async def register_entity(self, kb_id: UUID, entity: CanonicalEntity) -> CanonicalEntity: ...

    async def get_all_distinct(self, kb_id: UUID) -> list[CanonicalEntity]: ...

    async def find_matching(
        self, kb_id: UUID, name: str, entity_type: str
    ) -> CanonicalEntity | None: ...
