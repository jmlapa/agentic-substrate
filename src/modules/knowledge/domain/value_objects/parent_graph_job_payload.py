from typing import Any
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
    content: str = ""
    content_storage_path: str | None = None
    ontology: dict[str, Any] | None = None
    metadata: dict[str, Any] = {}
