import asyncio
import logging
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

logger = logging.getLogger(__name__)


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

        # 4. Merge sequential [:NEXT] edges in batch between consecutive Parent Chunks
        if len(document.parents) > 1:
            pairs = [
                {"p1_id": document.parents[i].id, "p2_id": document.parents[i + 1].id}
                for i in range(len(document.parents) - 1)
            ]
            batch_next_query = (
                "UNWIND $pairs AS pair "
                "MATCH (p1:ParentChunk {id: pair.p1_id}), (p2:ParentChunk {id: pair.p2_id}) "
                "MERGE (p1)-[r:NEXT]->(p2)"
            )
            graph_handle.query(batch_next_query, {"pairs": pairs})
            edges_count += len(pairs)

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
        except Exception as e:
            logger.error("Failed to query subgraph in FalkorDB: %s", e, exc_info=True)
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
        self,
        kb_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
        candidate_k: int = 50,
    ) -> list[HybridSearchResult]:
        if not query_embedding:
            return []

        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))
        query = (
            "CALL db.idx.vector.queryNodes('ChildChunk', 'embedding', "
            "$candidate_k, vecf32($query_vec)) "
            "YIELD node AS child, score AS vec_score "
            "MATCH (p_seed:ParentChunk)-[:CONTAINS_CHILD]->(child) "
            "WITH p_seed, max(1.0 - vec_score) AS seed_score "
            "ORDER BY seed_score DESC "
            "OPTIONAL MATCH (p_seed)-[:MENTIONS]->(e)<-[:MENTIONS]-(p_neighbor:ParentChunk) "
            "WHERE p_neighbor <> p_seed "
            "WITH p_seed, seed_score, p_neighbor, count(DISTINCT e) AS shared_entities "
            "ORDER BY shared_entities DESC "
            "WITH p_seed, seed_score, "
            "collect(DISTINCT {parent: p_neighbor, "
            "shared_entities: shared_entities})[0..5] AS top_neighbors "
            "UNWIND (CASE WHEN size(top_neighbors) > 0 THEN top_neighbors "
            "ELSE [{parent: null, shared_entities: 0}] END) AS tn "
            "WITH collect(DISTINCT {parent: p_seed, base_score: seed_score, "
            "is_seed: true, shared_entities: 0}) + "
            "     collect(DISTINCT {parent: tn.parent, base_score: seed_score * 0.7, "
            "is_seed: false, shared_entities: tn.shared_entities}) AS raw_candidates "
            "UNWIND raw_candidates AS c "
            "WITH c.parent AS p, max(c.base_score) AS base_score, "
            "max(c.shared_entities) AS shared_entities, max(c.is_seed) AS is_seed "
            "WHERE p IS NOT NULL "
            "WITH p, "
            "     CASE WHEN is_seed THEN base_score "
            "          ELSE (base_score * (1.0 + (CASE WHEN shared_entities > 5 "
            "THEN 5 ELSE shared_entities END * 0.05))) "
            "     END AS fused_score, "
            "     is_seed "
            "ORDER BY fused_score DESC "
            "LIMIT $top_k "
            "OPTIONAL MATCH (p)-[:MENTIONS]->(e1) "
            "OPTIONAL MATCH (e1)-[r]->(e2) "
            "OPTIONAL MATCH (d:Document)-[:HAS_PARENT]->(p) "
            "OPTIONAL MATCH (p)-[:NEXT]->(next_p:ParentChunk) "
            "OPTIONAL MATCH (prev_p:ParentChunk)-[:NEXT]->(p) "
            "RETURN p.id AS parent_id, "
            "       coalesce(d.id, '') AS document_id, "
            "       coalesce(d.name, '') AS document_name, "
            "       p.header_path AS header_path, "
            "       p.content AS parent_content, "
            "       fused_score AS relevance_score, "
            "       prev_p.id AS prev_chunk_id, "
            "       next_p.id AS next_chunk_id, "
            "       is_seed AS is_seed, "
            "       collect(DISTINCT CASE WHEN e1 IS NOT NULL AND r IS NOT NULL AND "
            "e2 IS NOT NULL THEN (coalesce(e1.name, e1.id, '') + ' ' + type(r) + ' ' + "
            "coalesce(e2.name, e2.id, '')) ELSE null END)[0..5] AS related_triples, "
            "       collect(DISTINCT CASE WHEN e1 IS NOT NULL THEN {type: labels(e1)[0], "
            "properties: properties(e1)} ELSE null END) AS related_entities "
            "ORDER BY relevance_score DESC"
        )

        try:
            res = graph_handle.query(
                query,
                {
                    "candidate_k": candidate_k,
                    "top_k": top_k,
                    "query_vec": query_embedding,
                },
            )
        except Exception as e:
            logger.error("Failed to query hybrid search in FalkorDB: %s", e, exc_info=True)
            return []

        results: list[HybridSearchResult] = []
        for row in res.result_set:
            if len(row) >= 11:
                parent_id = str(row[0])
                doc_id = str(row[1]) if row[1] is not None else ""
                doc_name = str(row[2]) if row[2] is not None else ""
                header_path = str(row[3]) if row[3] is not None else ""
                parent_content = str(row[4]) if row[4] is not None else ""
                relevance_score = float(row[5]) if row[5] is not None else 0.0
                prev_id = str(row[6]) if row[6] is not None else None
                next_id = str(row[7]) if row[7] is not None else None
                is_seed = bool(row[8]) if row[8] is not None else True
                raw_triples = row[9] if isinstance(row[9], list) else []
                raw_entities = row[10] if isinstance(row[10], list) else []

                # Filter clean triples and entities
                triples: list[str] = [
                    str(t)
                    for t in raw_triples
                    if t and str(t) != "None" and not str(t).startswith("None")
                ]
                entities: list[dict[str, Any]] = [
                    e for e in raw_entities if isinstance(e, dict) and e.get("type") is not None
                ]

                results.append(
                    HybridSearchResult(
                        parent_chunk_id=parent_id,
                        document_id=doc_id,
                        document_name=doc_name,
                        header_path=header_path,
                        parent_content=parent_content,
                        relevance_score=relevance_score,
                        retrieval_source="vector_match" if is_seed else "graph_expansion",
                        prev_chunk_id=prev_id,
                        next_chunk_id=next_id,
                        related_triples=triples,
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
        self,
        kb_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
        candidate_k: int = 50,
    ) -> list[HybridSearchResult]:
        return await asyncio.to_thread(
            self._query_hybrid_sync, kb_id, query_embedding, top_k, candidate_k
        )
