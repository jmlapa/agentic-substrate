from pydantic import BaseModel, Field

from .data_source_run_item_dto import DataSourceRunItemDTO


class ListDataSourceRunsResponse(BaseModel):
    runs: list[DataSourceRunItemDTO] = Field(default_factory=list)
