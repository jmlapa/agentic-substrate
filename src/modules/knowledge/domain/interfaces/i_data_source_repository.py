from typing import Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.entities.data_source import DataSource


@runtime_checkable
class IDataSourceRepository(Protocol):
    async def save(self, data_source: DataSource) -> None: ...

    async def get_by_id(self, data_source_id: UUID) -> DataSource | None: ...

    async def list_by_kb_id(self, kb_id: UUID) -> list[DataSource]: ...

    async def delete(self, data_source_id: UUID) -> bool: ...
