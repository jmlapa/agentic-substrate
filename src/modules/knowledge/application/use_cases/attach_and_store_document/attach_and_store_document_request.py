from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AttachAndStoreDocumentRequest(BaseModel):
    kb_id: UUID
    file_name: str
    content_type: str
    file_content: bytes
    enable_ocr: bool = False
    ocr_instructions: str | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
