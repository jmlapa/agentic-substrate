from pydantic import BaseModel, Field

from src.modules.knowledge.application.use_cases.list_data_sources.data_source_item_dto import (
    DataSourceItemDTO,
)


class ListDataSourcesResponse(BaseModel):
    data_sources: list[DataSourceItemDTO] = Field(default_factory=list)
