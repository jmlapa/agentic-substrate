from uuid import UUID

from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.interfaces.i_data_source_repository import (
    IDataSourceRepository,
)


class InMemoryDataSourceRepository(IDataSourceRepository):
    def __init__(self) -> None:
        self._data_sources: dict[UUID, DataSource] = {}

    async def save(self, data_source: DataSource) -> None:
        self._data_sources[data_source.id] = data_source

    async def get_by_id(self, data_source_id: UUID) -> DataSource | None:
        return self._data_sources.get(data_source_id)

    async def list_by_kb_id(self, kb_id: UUID) -> list[DataSource]:
        return [ds for ds in self._data_sources.values() if ds.kb_id == kb_id]

    async def delete(self, data_source_id: UUID) -> bool:
        return self._data_sources.pop(data_source_id, None) is not None
