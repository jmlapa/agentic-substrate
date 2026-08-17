from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)
from src.modules.knowledge.domain.value_objects.structural_graph_document import (
    StructuralGraphDocument,
)


@runtime_checkable
class IGraphStore(Protocol):
    async def store_graph(self, kb_id: UUID, graph: ExtractedGraph) -> tuple[int, int]: ...

    async def query_subgraph(
        self, kb_id: UUID, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]: ...

    async def ensure_vector_index(
        self,
        kb_id: UUID,
        dimension: int = 768,
        similarity_function: str = "cosine",
    ) -> None: ...

    async def store_structural_document(
        self, kb_id: UUID, document: StructuralGraphDocument
    ) -> tuple[int, int]: ...

    async def store_parent_mentions(
        self, kb_id: UUID, parent_chunk_id: str, graph: ExtractedGraph
    ) -> tuple[int, int]: ...

    async def query_hybrid(
        self, kb_id: UUID, query_embedding: list[float], top_k: int = 5
    ) -> list[HybridSearchResult]: ...
