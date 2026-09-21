from uuid import UUID

from pydantic import BaseModel


class DeleteDataSourceResponse(BaseModel):
    data_source_id: UUID
    success: bool
