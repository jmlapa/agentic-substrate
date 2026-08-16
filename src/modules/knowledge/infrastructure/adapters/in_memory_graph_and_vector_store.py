from collections import defaultdict
from typing import Any
from uuid import UUID

from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_vector_store import IVectorStore
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph


class InMemoryGraphAndVectorStore(IGraphStore, IVectorStore):
    def __init__(self) -> None:
        self._graphs: dict[UUID, ExtractedGraph] = defaultdict(
            lambda: ExtractedGraph(nodes=[], edges=[])
        )

    async def store_graph(self, kb_id: UUID, graph: ExtractedGraph) -> tuple[int, int]:
        current = self._graphs[kb_id]
        self._graphs[kb_id] = ExtractedGraph(
            nodes=current.nodes + graph.nodes,
            edges=current.edges + graph.edges,
        )
        return len(graph.nodes), len(graph.edges)

    async def store_node_embeddings(self, kb_id: UUID, graph: ExtractedGraph) -> int:
        return len(graph.nodes)

    async def query_subgraph(self, kb_id: UUID, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        graph = self._graphs.get(kb_id, ExtractedGraph(nodes=[], edges=[]))
        return [
            {
                "id": node.id,
                "node_type": node.node_type,
                "properties": node.properties,
            }
            for node in graph.nodes[:top_k]
        ]

    async def search_similar_nodes(
        self, kb_id: UUID, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        graph = self._graphs.get(kb_id, ExtractedGraph(nodes=[], edges=[]))
        return [
            {
                "id": node.id,
                "score": 0.95,
                "node_type": node.node_type,
                "properties": node.properties,
            }
            for node in graph.nodes[:top_k]
        ]
