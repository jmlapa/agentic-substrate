from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph


@runtime_checkable
class IVectorStore(Protocol):
    async def store_node_embeddings(self, kb_id: UUID, graph: ExtractedGraph) -> int: ...

    async def search_similar_nodes(
        self, kb_id: UUID, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]: ...
