from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ParentGraphJobPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    kb_id: UUID
    document_id: UUID
    storage_partition: str
    parent_id: str
    parent_index: int
    total_parents: int
    header_path: str
    content: str
