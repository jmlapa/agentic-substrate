from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk


@runtime_checkable
class IVectorStore(Protocol):
    async def store_node_embeddings(self, kb_id: UUID, graph: ExtractedGraph) -> int: ...

    async def search_similar_nodes(
        self, kb_id: UUID, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]: ...

    async def store_document_chunks(
        self,
        kb_id: UUID,
        document_id: UUID,
        chunks: list[ChildChunk],
        parent_chunks: list[ParentChunk] | None = None,
    ) -> int: ...

    async def search_similar_chunks(
        self,
        kb_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
        document_ids: list[UUID] | None = None,
    ) -> list[dict[str, Any]]: ...
