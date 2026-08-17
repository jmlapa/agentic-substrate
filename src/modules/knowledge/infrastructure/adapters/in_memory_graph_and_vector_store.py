from collections import defaultdict
from typing import Any
from uuid import UUID

from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_vector_store import IVectorStore
from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk
from src.modules.knowledge.domain.value_objects.structural_graph_document import (
    StructuralGraphDocument,
)


class InMemoryGraphAndVectorStore(IGraphStore, IVectorStore):
    def __init__(self) -> None:
        self._graphs: dict[UUID, ExtractedGraph] = defaultdict(
            lambda: ExtractedGraph(nodes=[], edges=[])
        )
        self._chunks: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
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

    async def query_hybrid(
        self, kb_id: UUID, query_embedding: list[float], top_k: int = 5
    ) -> list[HybridSearchResult]:
        results: list[HybridSearchResult] = []
        docs = self._structural_docs.get(kb_id, [])
        for doc in docs:
            for parent in doc.parents:
                entities = self._parent_mentions[kb_id].get(parent.id, [])
                results.append(
                    HybridSearchResult(
                        parent_chunk_id=parent.id,
                        header_path=parent.header_path,
                        parent_content=parent.content,
                        relevance_score=0.92,
                        related_entities=entities,
                    )
                )
        return results[:top_k]

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

    async def store_document_chunks(
        self,
        kb_id: UUID,
        document_id: UUID,
        chunks: list[ChildChunk],
        parent_chunks: list[ParentChunk] | None = None,
    ) -> int:
        parent_map = {p.id: p.content for p in (parent_chunks or [])}
        for chunk in chunks:
            self._chunks[kb_id].append(
                {
                    "id": chunk.id,
                    "document_id": document_id,
                    "parent_chunk_id": chunk.parent_chunk_id,
                    "chunk_index": chunk.chunk_index,
                    "header_path": chunk.header_path,
                    "content": chunk.content,
                    "parent_content": parent_map.get(chunk.parent_chunk_id, ""),
                    "embedding": chunk.embedding,
                    "metadata": chunk.metadata,
                }
            )
        return len(chunks)

    async def search_similar_chunks(
        self,
        kb_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
        document_ids: list[UUID] | None = None,
    ) -> list[dict[str, Any]]:
        all_chunks = self._chunks.get(kb_id, [])
        filtered = all_chunks
        if document_ids is not None:
            doc_set = set(document_ids)
            filtered = [c for c in all_chunks if c["document_id"] in doc_set]

        results: list[dict[str, Any]] = []
        for c in filtered[:top_k]:
            results.append(
                {
                    "id": c["id"],
                    "document_id": c["document_id"],
                    "score": 0.92,
                    "parent_chunk_id": c["parent_chunk_id"],
                    "chunk_index": c["chunk_index"],
                    "header_path": c["header_path"],
                    "content": c["content"],
                    "parent_content": c["parent_content"],
                    "metadata": c["metadata"],
                }
            )
        return results
