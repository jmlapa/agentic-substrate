from collections import defaultdict
from typing import Any
from uuid import UUID

from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)
from src.modules.knowledge.domain.value_objects.structural_graph_document import (
    StructuralGraphDocument,
)


class InMemoryGraphStore(IGraphStore):
    def __init__(self) -> None:
        self._graphs: dict[UUID, ExtractedGraph] = defaultdict(
            lambda: ExtractedGraph(nodes=[], edges=[])
        )
        self._structural_docs: dict[UUID, list[StructuralGraphDocument]] = defaultdict(list)
        self._parent_mentions: dict[UUID, dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )

    async def ensure_vector_index(
        self,
        kb_id: UUID,
        dimension: int = 768,
        similarity_function: str = "cosine",
    ) -> None:
        pass

    async def store_graph(self, kb_id: UUID, graph: ExtractedGraph) -> tuple[int, int]:
        current = self._graphs[kb_id]
        self._graphs[kb_id] = ExtractedGraph(
            nodes=current.nodes + graph.nodes,
            edges=current.edges + graph.edges,
        )
        return len(graph.nodes), len(graph.edges)

    async def store_structural_document(
        self, kb_id: UUID, document: StructuralGraphDocument
    ) -> tuple[int, int]:
        self._structural_docs[kb_id].append(document)
        nodes_count = 1 + len(document.parents) + len(document.children)
        edges_count = len(document.parents) + len(document.children)
        return nodes_count, edges_count

    async def store_parent_mentions(
        self, kb_id: UUID, parent_chunk_id: str, graph: ExtractedGraph
    ) -> tuple[int, int]:
        for node in graph.nodes:
            self._parent_mentions[kb_id][parent_chunk_id].append(
                {"type": node.node_type, "properties": node.properties}
            )
        await self.store_graph(kb_id, graph)
        return len(graph.nodes), len(graph.edges) + len(graph.nodes)

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

    async def query_hybrid(
        self,
        kb_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
        candidate_k: int = 50,
    ) -> list[HybridSearchResult]:
        results: list[HybridSearchResult] = []
        docs = self._structural_docs.get(kb_id, [])
        for doc in docs:
            for idx, parent in enumerate(doc.parents):
                entities = self._parent_mentions[kb_id].get(parent.id, [])
                prev_id = doc.parents[idx - 1].id if idx > 0 else None
                next_id = doc.parents[idx + 1].id if idx < len(doc.parents) - 1 else None
                results.append(
                    HybridSearchResult(
                        parent_chunk_id=parent.id,
                        document_id=str(doc.document_id),
                        document_name=doc.document_name,
                        header_path=parent.header_path,
                        parent_content=parent.content,
                        relevance_score=0.92,
                        retrieval_source="vector_match",
                        prev_chunk_id=prev_id,
                        next_chunk_id=next_id,
                        related_triples=[],
                        related_entities=entities,
                    )
                )
        return results[:top_k]

    async def delete_document_subgraph(self, kb_id: UUID, document_id: UUID) -> None:
        if kb_id in self._structural_docs:
            docs = self._structural_docs[kb_id]
            removed_parents: set[str] = set()
            new_docs: list[StructuralGraphDocument] = []
            for doc in docs:
                if doc.document_id == document_id:
                    for p in doc.parents:
                        removed_parents.add(p.id)
                else:
                    new_docs.append(doc)
            self._structural_docs[kb_id] = new_docs
            if kb_id in self._parent_mentions:
                for p_id in removed_parents:
                    self._parent_mentions[kb_id].pop(p_id, None)

    async def delete_graph(self, kb_id: UUID) -> None:
        self._graphs.pop(kb_id, None)
        self._structural_docs.pop(kb_id, None)
        self._parent_mentions.pop(kb_id, None)
