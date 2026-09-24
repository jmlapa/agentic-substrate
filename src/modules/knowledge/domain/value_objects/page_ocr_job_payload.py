from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PageOcrJobPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    kb_id: UUID
    document_id: UUID
    storage_partition: str
    raw_storage_path: str
    page_number: int
    total_pages: int
    hierarchy_hint: str | None = None
    effective_prompt: str = ""
    page_image_storage_path: str | None = None
