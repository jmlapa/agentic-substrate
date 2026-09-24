from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RetryFailedDataSourceItemsRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    kb_id: UUID
    data_source_id: UUID
    run_id: UUID
