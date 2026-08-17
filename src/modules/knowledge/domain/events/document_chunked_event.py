from typing import Any
from uuid import UUID

from pydantic import Field

from src.kernel.domain.domain_event import DomainEvent


class DocumentChunkedEvent(DomainEvent):
    document_id: UUID
    total_parents: int
    total_children: int
    chunks_summary: list[dict[str, Any]] = Field(default_factory=list)
