from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph


@runtime_checkable
class IGraphStore(Protocol):
    async def store_graph(self, kb_id: UUID, graph: ExtractedGraph) -> tuple[int, int]: ...

    async def query_subgraph(
        self, kb_id: UUID, query: str, top_k: int = 5
    ) -> list[dict[str, Any]]: ...
