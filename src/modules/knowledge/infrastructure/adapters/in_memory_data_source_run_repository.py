from uuid import UUID

from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.interfaces.i_data_source_run_repository import (
    IDataSourceRunRepository,
)


class InMemoryDataSourceRunRepository(IDataSourceRunRepository):
    def __init__(self) -> None:
        self._runs: dict[UUID, DataSourceRun] = {}

    async def save(self, run: DataSourceRun) -> None:
        self._runs[run.id] = run

    async def get_by_id(self, run_id: UUID) -> DataSourceRun | None:
        return self._runs.get(run_id)

    async def list_by_data_source_id(
        self, data_source_id: UUID, limit: int = 50
    ) -> list[DataSourceRun]:
        matching = [
            r for r in self._runs.values() if r.data_source_id == data_source_id
        ]
        matching.sort(key=lambda r: r.started_at, reverse=True)
        return matching[:limit]
