from typing import Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun


@runtime_checkable
class IDataSourceRunRepository(Protocol):
    async def save(self, run: DataSourceRun) -> None: ...

    async def get_by_id(self, run_id: UUID) -> DataSourceRun | None: ...

    async def list_by_data_source_id(
        self, data_source_id: UUID, limit: int = 50
    ) -> list[DataSourceRun]: ...
