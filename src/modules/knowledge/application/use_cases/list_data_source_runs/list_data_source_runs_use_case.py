from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Ok, Result
from src.modules.knowledge.domain.interfaces.i_data_source_run_repository import (
    IDataSourceRunRepository,
)

from .data_source_run_item_dto import DataSourceRunItemDTO
from .list_data_source_runs_request import ListDataSourceRunsRequest
from .list_data_source_runs_response import ListDataSourceRunsResponse


class ListDataSourceRunsUseCase:
    def __init__(self, run_repository: IDataSourceRunRepository) -> None:
        self._run_repo = run_repository

    async def execute(
        self, request: ListDataSourceRunsRequest
    ) -> Result[ListDataSourceRunsResponse, DomainError]:
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
