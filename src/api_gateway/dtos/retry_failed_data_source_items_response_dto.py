from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RetryFailedDataSourceItemsResponseDto(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_source_id: UUID
    run_id: UUID
    reprocessed_count: int
    remaining_failed_count: int
    status: str
