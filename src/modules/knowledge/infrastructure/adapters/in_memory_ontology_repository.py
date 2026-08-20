from uuid import UUID

from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)
from src.modules.knowledge.domain.ontology.ontology_template import OntologyTemplate


class InMemoryOntologyRepository(IOntologyRepository):
    def __init__(self) -> None:
        self._templates: dict[UUID, OntologyTemplate] = {}

    async def save(self, ontology: OntologyTemplate) -> None:
        self._templates[ontology.id] = ontology

    async def get_by_id(self, id: UUID) -> OntologyTemplate | None:
        return self._templates.get(id)

    async def get_by_name_and_version(self, name: str, version: int) -> OntologyTemplate | None:
        return next(
            (
                t
                for t in self._templates.values()
                if t.name.lower() == name.lower() and t.version == version
            ),
            None,
        )

    async def list_all(self) -> list[OntologyTemplate]:
        return list(self._templates.values())

    async def delete_by_id(self, id: UUID) -> None:
        self._templates.pop(id, None)

    async def count_usages(self, ontology_id: UUID) -> int:
        # Defaults to 0 in mock/in-memory unless mocked
        return 0
