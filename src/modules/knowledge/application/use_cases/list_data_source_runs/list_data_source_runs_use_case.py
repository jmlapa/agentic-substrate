from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.domain.interfaces.i_data_source_repository import (
    IDataSourceRepository,
)
from src.modules.knowledge.domain.interfaces.i_data_source_run_repository import (
    IDataSourceRunRepository,
)

from .data_source_run_item_dto import DataSourceRunItemDTO
from .list_data_source_runs_request import ListDataSourceRunsRequest
from .list_data_source_runs_response import ListDataSourceRunsResponse


class ListDataSourceRunsUseCase:
    def __init__(
        self,
        run_repository: IDataSourceRunRepository,
        data_source_repository: IDataSourceRepository | None = None,
    ) -> None:
        self._run_repo = run_repository
        self._ds_repo = data_source_repository

    async def execute(
        self, request: ListDataSourceRunsRequest
    ) -> Result[ListDataSourceRunsResponse, DomainError]:
        if self._ds_repo is not None:
            ds = await self._ds_repo.get_by_id(request.data_source_id)
            if ds is None or (request.kb_id is not None and ds.kb_id != request.kb_id):
                return Err(
                    DomainError(
                        f"DataSource '{request.data_source_id}' não encontrado.",
                        "DATA_SOURCE_NOT_FOUND",
                    )
                )

        runs = await self._run_repo.list_by_data_source_id(
            request.data_source_id, limit=request.limit
        )
        dtos = [
            DataSourceRunItemDTO(
                id=run.id,
                data_source_id=run.data_source_id,
                kb_id=run.kb_id,
                status=run.status.value,
                total_files_discovered=run.total_files_discovered,
                indexed_files_count=run.indexed_files_count,
                failed_files_count=run.failed_files_count,
                failure_summary=run.failure_summary,
                started_at=run.started_at,
                completed_at=run.completed_at,
            )
            for run in runs
        ]
        return Ok(ListDataSourceRunsResponse(runs=dtos))
