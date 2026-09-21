from pydantic import Field

from src.kernel.domain.value_object import ValueObject
from src.modules.knowledge.domain.value_objects.discovered_document_item import (
    DiscoveredDocumentItem,
)


class DataSourceChangesBatch(ValueObject):
    items: list[DiscoveredDocumentItem]
    next_cursor: str | None = None
    deleted_external_ids: list[str] = Field(default_factory=list)
