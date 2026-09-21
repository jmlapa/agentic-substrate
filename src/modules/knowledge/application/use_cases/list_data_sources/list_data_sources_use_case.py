from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Ok, Result
from src.modules.knowledge.domain.interfaces.i_data_source_repository import (
    IDataSourceRepository,
)

from .data_source_item_dto import DataSourceItemDTO
from .list_data_sources_request import ListDataSourcesRequest
from .list_data_sources_response import ListDataSourcesResponse


class ListDataSourcesUseCase:
    def __init__(self, data_source_repository: IDataSourceRepository) -> None:
        self._ds_repo = data_source_repository

    async def execute(
        self, request: ListDataSourcesRequest
    ) -> Result[ListDataSourcesResponse, DomainError]:
        items = await self._ds_repo.list_by_kb_id(request.kb_id)
        dtos = [
            DataSourceItemDTO(
                id=ds.id,
                kb_id=ds.kb_id,
                name=ds.name,
                data_source_type=ds.data_source_type.value,
                status=ds.status.value,
                cursor=ds.cursor,
                sync_interval_minutes=ds.sync_interval_minutes,
                last_synced_at=ds.last_synced_at,
                error_message=ds.error_message,
                config=ds.config,
                created_at=ds.created_at,
                updated_at=ds.updated_at,
            )
            for ds in items
        ]
        return Ok(ListDataSourcesResponse(data_sources=dtos))
