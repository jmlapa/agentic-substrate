import asyncio
import re
from typing import Any
from uuid import UUID

from falkordb import FalkorDB

from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)
from src.modules.knowledge.domain.value_objects.structural_graph_document import (
    StructuralGraphDocument,
)


class FalkorDbGraphStoreAdapter(IGraphStore):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6380,
        client: Any | None = None,
    ) -> None:
        self._client = client or FalkorDB(host=host, port=port)

    def _sanitize_identifier(self, identifier: str) -> str:
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", identifier)
        return sanitized if sanitized else "Entity"

    def _get_graph_name(self, kb_id: UUID) -> str:
        return f"kb_{str(kb_id).replace('-', '_')}"

    def _ensure_vector_index_sync(
        self, kb_id: UUID, dimension: int = 768, similarity_function: str = "cosine"
    ) -> None:
        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))
        query = (
            f"CREATE VECTOR INDEX FOR (c:ChildChunk) ON (c.embedding) "
            f"OPTIONS {{dimension: {dimension}, similarityFunction: '{similarity_function}'}}"
        )
        try:
            graph_handle.query(query)
        except Exception:
            # Ignore if index already exists
            pass

    def _store_graph_sync(self, kb_id: UUID, graph: ExtractedGraph) -> tuple[int, int]:
        if not graph.nodes and not graph.edges:
            return 0, 0

        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))

        # 1. Upsert nodes
        for node in graph.nodes:
            label = self._sanitize_identifier(node.node_type)
            query = f"MERGE (n:{label} {{id: $id}}) SET n += $props"
            graph_handle.query(query, {"id": node.id, "props": node.properties})

        # 2. Upsert edges
        for edge in graph.edges:
            rel_type = self._sanitize_identifier(edge.relationship_type.upper())
            query = (
                f"MATCH (src {{id: $src_id}}), (dst {{id: $dst_id}}) "
                f"MERGE (src)-[r:{rel_type}]->(dst) "
                f"SET r += $props"
            )
            graph_handle.query(
                query,
                {
                    "src_id": edge.source_id,
                    "dst_id": edge.target_id,
                    "props": edge.properties,
                },
            )

        return len(graph.nodes), len(graph.edges)

    def _store_structural_document_sync(
        self, kb_id: UUID, document: StructuralGraphDocument
    ) -> tuple[int, int]:
        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))

        doc_id_str = str(document.document_id)
        kb_id_str = str(kb_id)

        # 1. Merge Document Node
        doc_query = (
            "MERGE (d:Document {id: $doc_id}) "
            "SET d.kb_id = $kb_id, d.name = $name, "
            "d.total_parents = $total_parents, d.total_children = $total_children"
        )
        graph_handle.query(
            doc_query,
            {
                "doc_id": doc_id_str,
                "kb_id": kb_id_str,
                "name": document.document_name,
                "total_parents": len(document.parents),
                "total_children": len(document.children),
            },
        )

        nodes_count = 1 + len(document.parents) + len(document.children)
        edges_count = 0

        # 2. Merge Parent Chunks & HAS_PARENT edges
        for parent in document.parents:
            p_query = (
                "MATCH (d:Document {id: $doc_id}) "
                "MERGE (p:ParentChunk {id: $parent_id}) "
                "SET p.kb_id = $kb_id, p.document_id = $doc_id, "
                "p.header_path = $header_path, p.content = $content, p.token_count = $token_count "
                "MERGE (d)-[r:HAS_PARENT]->(p)"
            )
            graph_handle.query(
                p_query,
                {
                    "doc_id": doc_id_str,
                    "kb_id": kb_id_str,
                    "parent_id": parent.id,
                    "header_path": parent.header_path,
                    "content": parent.content,
                    "token_count": parent.token_count,
                },
            )
            edges_count += 1

        # 3. Merge Child Chunks & CONTAINS_CHILD edges
        for child in document.children:
            c_query = (
                "MATCH (p:ParentChunk {id: $parent_id}) "
                "MERGE (c:ChildChunk {id: $child_id}) "
                "SET c.kb_id = $kb_id, c.parent_chunk_id = $parent_id, "
                "c.chunk_index = $chunk_index, c.header_path = $header_path, "
                "c.content = $content, c.embedding = vecf32($embedding) "
                "MERGE (p)-[r:CONTAINS_CHILD]->(c)"
            )
            graph_handle.query(
                c_query,
                {
                    "parent_id": child.parent_chunk_id,
                    "child_id": child.id,
                    "kb_id": kb_id_str,
                    "chunk_index": child.chunk_index,
                    "header_path": child.header_path,
                    "content": child.content,
                    "embedding": child.embedding or [],
                },
            )
            edges_count += 1

        return nodes_count, edges_count

    def _store_parent_mentions_sync(
        self, kb_id: UUID, parent_chunk_id: str, graph: ExtractedGraph
    ) -> tuple[int, int]:
        if not graph.nodes and not graph.edges:
            return 0, 0

        # Store graph entities first
        nodes_stored, edges_stored = self._store_graph_sync(kb_id, graph)

        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))

        # Link parent chunk to each extracted entity
        mention_edges = 0
        for node in graph.nodes:
            query = (
                "MATCH (p:ParentChunk {id: $parent_id}), (e {id: $entity_id}) "
                "MERGE (p)-[r:MENTIONS]->(e)"
            )
            graph_handle.query(
                query,
                {
                    "parent_id": parent_chunk_id,
                    "entity_id": node.id,
                },
            )
            mention_edges += 1

        return nodes_stored, edges_stored + mention_edges

    def _query_subgraph_sync(self, kb_id: UUID, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))
        is_cypher = query.strip().upper().startswith(("MATCH", "RETURN", "WITH", "UNWIND"))

        if is_cypher:
            cypher_query = query
        else:
            cypher_query = f"MATCH (n) RETURN n LIMIT {top_k}"

        try:
            res = graph_handle.query(cypher_query)
        except Exception:
            return []

        results: list[dict[str, Any]] = []
        for row in res.result_set:
            for item in row:
                if hasattr(item, "properties") and hasattr(item, "labels"):
                    results.append(
                        {
                            "id": item.properties.get("id", ""),
                            "node_type": item.labels[0] if item.labels else "Unknown",
                            "properties": item.properties,
                        }
                    )
                elif isinstance(item, dict):
                    results.append(item)
        return results[:top_k]

    def _query_hybrid_sync(
        self, kb_id: UUID, query_embedding: list[float], top_k: int = 5
    ) -> list[HybridSearchResult]:
        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))
        query = (
            "CALL db.idx.vector.queryNodes('ChildChunk', 'embedding', $top_k, vecf32($query_vec)) "
            "YIELD node AS child, score "
            "MATCH (parent:ParentChunk)-[:CONTAINS_CHILD]->(child) "
            "OPTIONAL MATCH (parent)-[:MENTIONS]->(entity) "
            "RETURN parent.id AS parent_id, "
            "       parent.header_path AS header_path, "
            "       parent.content AS parent_content, "
            "       collect(DISTINCT {type: labels(entity)[0], "
            "properties: properties(entity)}) AS related_entities, "
            "       max(score) AS relevance_score "
            "ORDER BY relevance_score DESC"
        )
        try:
            res = graph_handle.query(query, {"top_k": top_k, "query_vec": query_embedding})
        except Exception:
            return []

        results: list[HybridSearchResult] = []
        for row in res.result_set:
            # row: [parent_id, header_path, parent_content, related_entities, relevance_score]
            if len(row) >= 5:
                parent_id = str(row[0])
                header_path = str(row[1]) if row[1] is not None else ""
                parent_content = str(row[2]) if row[2] is not None else ""
                raw_entities = row[3] if isinstance(row[3], list) else []
                # filter out empty null entities resulting from OPTIONAL MATCH
                entities: list[dict[str, Any]] = [
                    e for e in raw_entities if isinstance(e, dict) and e.get("type") is not None
                ]
                relevance_score = float(row[4]) if row[4] is not None else 0.0

                results.append(
                    HybridSearchResult(
                        parent_chunk_id=parent_id,
                        header_path=header_path,
                        parent_content=parent_content,
                        relevance_score=relevance_score,
                        related_entities=entities,
                    )
                )
        return results

    async def ensure_vector_index(
        self, kb_id: UUID, dimension: int = 768, similarity_function: str = "cosine"
    ) -> None:
        await asyncio.to_thread(
            self._ensure_vector_index_sync, kb_id, dimension, similarity_function
        )

    async def store_graph(self, kb_id: UUID, graph: ExtractedGraph) -> tuple[int, int]:
        return await asyncio.to_thread(self._store_graph_sync, kb_id, graph)

    async def store_structural_document(
        self, kb_id: UUID, document: StructuralGraphDocument
    ) -> tuple[int, int]:
        return await asyncio.to_thread(self._store_structural_document_sync, kb_id, document)

    async def store_parent_mentions(
        self, kb_id: UUID, parent_chunk_id: str, graph: ExtractedGraph
    ) -> tuple[int, int]:
        return await asyncio.to_thread(
            self._store_parent_mentions_sync, kb_id, parent_chunk_id, graph
        )

    async def query_subgraph(self, kb_id: UUID, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._query_subgraph_sync, kb_id, query, top_k)

    async def query_hybrid(
        self, kb_id: UUID, query_embedding: list[float], top_k: int = 5
    ) -> list[HybridSearchResult]:
        return await asyncio.to_thread(self._query_hybrid_sync, kb_id, query_embedding, top_k)
