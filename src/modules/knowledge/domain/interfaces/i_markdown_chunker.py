from typing import Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.value_objects.document_chunk_collection import (
    DocumentChunkCollection,
)
from src.modules.knowledge.domain.value_objects.document_source_type import (
    DocumentSourceType,
)


@runtime_checkable
class IMarkdownChunker(Protocol):
    async def chunk(
        self,
        document_id: UUID,
        document_name: str,
        markdown_text: str,
        source_type: DocumentSourceType | None = None,
        ingested_at: float | None = None,
    ) -> DocumentChunkCollection: ...
