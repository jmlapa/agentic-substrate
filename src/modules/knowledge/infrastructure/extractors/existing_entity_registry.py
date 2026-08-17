import asyncio
import unicodedata
from collections import defaultdict
from uuid import UUID

from src.modules.knowledge.domain.interfaces.i_entity_registry import (
    IEntityRegistry,
)
from src.modules.knowledge.domain.value_objects.canonical_entity import (
    CanonicalEntity,
)


class ExistingEntityRegistry(IEntityRegistry):
    """
    Catálogo em memória para canonização e deduplicação cumulativa de entidades de Knowledge Bases.
    Normaliza nomes e sinônimos (sem acentos e case-insensitive) para co-referência determinística.
    """

    def __init__(self) -> None:
        self._entities: dict[UUID, dict[str, CanonicalEntity]] = defaultdict(dict)
        self._normalized_index: dict[UUID, dict[tuple[str, str], str]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    @staticmethod
    def _normalize(text: str) -> str:
        # Remove acentos, pontuação inicial/final e converte para minúsculas
        nfkd = unicodedata.normalize("NFKD", text)
        ascii_text = nfkd.encode("ASCII", "ignore").decode("utf-8")
        return " ".join(ascii_text.lower().strip().split())

    async def register_entity(self, kb_id: UUID, entity: CanonicalEntity) -> CanonicalEntity:
        async with self._lock:
            kb_entities = self._entities[kb_id]
            norm_index = self._normalized_index[kb_id]

            # 1. Se o ID já existir, mescla aliases
            if entity.id in kb_entities:
                existing = kb_entities[entity.id]
                merged_aliases = sorted(set(existing.aliases + entity.aliases + [entity.name]))
                updated = CanonicalEntity(
                    id=existing.id,
                    name=existing.name,
                    entity_type=existing.entity_type,
                    aliases=merged_aliases,
                )
                kb_entities[entity.id] = updated

                # Atualiza índice para todos os aliases
                norm_type = self._normalize(existing.entity_type)
                for alias in merged_aliases + [existing.name]:
                    norm_index[(self._normalize(alias), norm_type)] = existing.id
                return updated

            # 2. Registra nova entidade
            all_aliases = sorted(set(entity.aliases + [entity.name]))
            new_entity = CanonicalEntity(
                id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                aliases=all_aliases,
            )
            kb_entities[entity.id] = new_entity

            norm_type = self._normalize(entity.entity_type)
            for alias in all_aliases:
                norm_index[(self._normalize(alias), norm_type)] = entity.id

            return new_entity

    async def get_all_distinct(self, kb_id: UUID) -> list[CanonicalEntity]:
        async with self._lock:
            return list(self._entities[kb_id].values())

    async def find_matching(
        self, kb_id: UUID, name: str, entity_type: str
    ) -> CanonicalEntity | None:
        async with self._lock:
            norm_name = self._normalize(name)
            norm_type = self._normalize(entity_type)

            entity_id = self._normalized_index[kb_id].get((norm_name, norm_type))
            if entity_id and entity_id in self._entities[kb_id]:
                return self._entities[kb_id][entity_id]

            return None
