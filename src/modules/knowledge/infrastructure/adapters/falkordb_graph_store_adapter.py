import asyncio
import logging
import re
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar
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

T = TypeVar("T")


class FalkorDbGraphStoreAdapter(IGraphStore):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6380,
        client: Any | None = None,
        max_workers: int = 64,
    ) -> None:
        self._client = client or FalkorDB(host=host, port=port)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="falkordb")

    def _sanitize_identifier(self, identifier: str) -> str:
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", identifier)
        return sanitized if sanitized else "Entity"

    def _get_graph_name(self, kb_id: UUID) -> str:
        return f"kb_{str(kb_id).replace('-', '_')}"

    def _ensure_vector_index_sync(
        self, kb_id: UUID, dimension: int = 768, similarity_function: str = "cosine"
    ) -> None:
        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))
        vector_query = (
            f"CREATE VECTOR INDEX FOR (c:ChildChunk) ON (c.embedding) "
            f"OPTIONS {{dimension: {dimension}, similarityFunction: '{similarity_function}'}}"
        )
        try:
            graph_handle.query(vector_query)
        except Exception:
            pass

        # Cria índices de range para queries filtradas de alta performance e lookup rápido de IDs
        range_queries = [
            "CREATE INDEX FOR (d:Document) ON (d.id)",
            "CREATE INDEX FOR (p:ParentChunk) ON (p.id)",
            "CREATE INDEX FOR (c:ChildChunk) ON (c.id)",
            "CREATE INDEX FOR (p:ParentChunk) ON (p.source_type)",
            "CREATE INDEX FOR (p:ParentChunk) ON (p.ingested_at)",
            "CREATE INDEX FOR (c:ChildChunk) ON (c.source_type)",
            "CREATE INDEX FOR (c:ChildChunk) ON (c.ingested_at)",
        ]
        for q in range_queries:
            try:
                graph_handle.query(q)
            except Exception:
                pass

    def _store_graph_sync(self, kb_id: UUID, graph: ExtractedGraph) -> tuple[int, int]:
        if not graph.nodes and not graph.edges:
            return 0, 0

        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))

        # 1. Upsert nodes em lote por label via UNWIND
        nodes_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for node in graph.nodes:
            label = self._sanitize_identifier(node.node_type)
            nodes_by_label[label].append({"id": node.id, "props": node.properties})

        for label, batch in nodes_by_label.items():
            query = f"UNWIND $batch AS item MERGE (n:{label} {{id: item.id}}) SET n += item.props"
            graph_handle.query(query, {"batch": batch})

        # 2. Upsert edges em lote por relationship_type via UNWIND
        edges_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in graph.edges:
            rel_type = self._sanitize_identifier(edge.relationship_type.upper())
            edges_by_type[rel_type].append(
                {
                    "src_id": edge.source_id,
                    "dst_id": edge.target_id,
                    "props": edge.properties,
                }
            )

        for rel_type, batch in edges_by_type.items():
            query = (
                f"UNWIND $batch AS item "
                f"MATCH (src {{id: item.src_id}}), (dst {{id: item.dst_id}}) "
                f"MERGE (src)-[r:{rel_type}]->(dst) "
                f"SET r += item.props"
            )
            graph_handle.query(query, {"batch": batch})

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

        # 2. Merge Parent Chunks em lote via UNWIND
        if document.parents:
            parents_data = [
                {
                    "id": p.id,
                    "header_path": p.header_path,
                    "content": p.content,
                    "token_count": p.token_count,
                    "source_type": p.metadata.get("source_type", "document"),
                    "ingested_at": p.metadata.get("ingested_at"),
                }
                for p in document.parents
            ]
            p_batch_query = (
                "MATCH (d:Document {id: $doc_id}) "
                "UNWIND $parents AS p_data "
                "MERGE (p:ParentChunk {id: p_data.id}) "
                "SET p.kb_id = $kb_id, p.document_id = $doc_id, "
                "p.header_path = p_data.header_path, p.content = p_data.content, "
                "p.token_count = p_data.token_count, "
                "p.source_type = p_data.source_type, p.ingested_at = p_data.ingested_at "
                "MERGE (d)-[r:HAS_PARENT]->(p)"
            )
            graph_handle.query(
                p_batch_query,
                {"doc_id": doc_id_str, "kb_id": kb_id_str, "parents": parents_data},
            )
            edges_count += len(document.parents)

        # 3. Merge Child Chunks em lote via UNWIND
        if document.children:
            children_data = [
                {
                    "id": c.id,
                    "parent_id": c.parent_chunk_id,
                    "chunk_index": c.chunk_index,
                    "header_path": c.header_path,
                    "content": c.content,
                    "embedding": c.embedding or [],
                    "source_type": c.metadata.get("source_type", "document"),
                    "ingested_at": c.metadata.get("ingested_at"),
                }
                for c in document.children
            ]
            c_batch_query = (
                "UNWIND $children AS c_data "
                "MATCH (p:ParentChunk {id: c_data.parent_id}) "
                "MERGE (c:ChildChunk {id: c_data.id}) "
                "SET c.kb_id = $kb_id, c.parent_chunk_id = c_data.parent_id, "
                "c.chunk_index = c_data.chunk_index, c.header_path = c_data.header_path, "
                "c.content = c_data.content, c.embedding = vecf32(c_data.embedding), "
                "c.source_type = c_data.source_type, c.ingested_at = c_data.ingested_at "
                "MERGE (p)-[r:CONTAINS_CHILD]->(c)"
            )
            graph_handle.query(
                c_batch_query,
                {"kb_id": kb_id_str, "children": children_data},
            )
            edges_count += len(document.children)

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

        # Link parent chunk to each extracted entity in batch via UNWIND
        mentions_data = [{"entity_id": node.id} for node in graph.nodes]
        mention_query = (
            "UNWIND $mentions AS m "
            "MATCH (p:ParentChunk {id: $parent_id}), (e {id: m.entity_id}) "
            "MERGE (p)-[r:MENTIONS]->(e)"
        )
        graph_handle.query(
            mention_query,
            {
                "parent_id": parent_chunk_id,
                "mentions": mentions_data,
            },
        )
        mention_edges = len(graph.nodes)

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
        source_types: list[str] | None = None,
        time_from: float | None = None,
        time_to: float | None = None,
        document_id: UUID | None = None,
    ) -> list[HybridSearchResult]:
        if not query_embedding:
            return []

        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))

        filter_clauses: list[str] = []
        params: dict[str, Any] = {
            "candidate_k": candidate_k,
            "top_k": top_k,
            "query_vec": query_embedding,
        }

        if document_id is not None:
            filter_clauses.append("p_seed.document_id = $document_id")
            params["document_id"] = str(document_id)
        if source_types:
            filter_clauses.append("p_seed.source_type IN $source_types")
            params["source_types"] = source_types
        if time_from is not None:
            filter_clauses.append("p_seed.ingested_at >= $time_from")
            params["time_from"] = time_from
        if time_to is not None:
            filter_clauses.append("p_seed.ingested_at <= $time_to")
            params["time_to"] = time_to

        where_filter = f"WHERE {' AND '.join(filter_clauses)} " if filter_clauses else ""

        query = (
            "CALL db.idx.vector.queryNodes('ChildChunk', 'embedding', "
            "$candidate_k, vecf32($query_vec)) "
            "YIELD node AS child, score AS vec_score "
            "MATCH (p_seed:ParentChunk)-[:CONTAINS_CHILD]->(child) "
            f"{where_filter}"
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
            "       coalesce(p.source_type, 'document') AS source_type, "
            "       p.ingested_at AS ingested_at, "
            "       collect(DISTINCT CASE WHEN e1 IS NOT NULL AND r IS NOT NULL AND "
            "e2 IS NOT NULL THEN (coalesce(e1.name, e1.id, '') + ' ' + type(r) + ' ' + "
            "coalesce(e2.name, e2.id, '')) ELSE null END)[0..5] AS related_triples, "
            "       collect(DISTINCT CASE WHEN e1 IS NOT NULL THEN {type: labels(e1)[0], "
            "properties: properties(e1)} ELSE null END) AS related_entities "
            "ORDER BY relevance_score DESC"
        )

        try:
            res = graph_handle.query(query, params)
        except Exception as e:
            logger.error("Failed to query hybrid search in FalkorDB: %s", e, exc_info=True)
            return []

        results: list[HybridSearchResult] = []
        for row in res.result_set:
            if len(row) >= 13:
                parent_id = str(row[0])
                doc_id = str(row[1]) if row[1] is not None else ""
                doc_name = str(row[2]) if row[2] is not None else ""
                header_path = str(row[3]) if row[3] is not None else ""
                parent_content = str(row[4]) if row[4] is not None else ""
                relevance_score = float(row[5]) if row[5] is not None else 0.0
                prev_id = str(row[6]) if row[6] is not None else None
                next_id = str(row[7]) if row[7] is not None else None
                is_seed = bool(row[8]) if row[8] is not None else True
                p_source_type = str(row[9]) if row[9] is not None else "document"
                p_ingested_at = float(row[10]) if row[10] is not None else None
                raw_triples = row[11] if isinstance(row[11], list) else []
                raw_entities = row[12] if isinstance(row[12], list) else []

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
                        source_type=p_source_type,
                        ingested_at=p_ingested_at,
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

    async def _run_async(self, func: Callable[..., T], *args: Any) -> T:
        loop = asyncio.get_running_loop()
        res: T = await loop.run_in_executor(self._executor, func, *args)
        return res

    def close(self) -> None:
        self._executor.shutdown(wait=False)

    async def ensure_vector_index(
        self, kb_id: UUID, dimension: int = 768, similarity_function: str = "cosine"
    ) -> None:
        await self._run_async(self._ensure_vector_index_sync, kb_id, dimension, similarity_function)

    async def store_graph(self, kb_id: UUID, graph: ExtractedGraph) -> tuple[int, int]:
        return await self._run_async(self._store_graph_sync, kb_id, graph)

    async def store_structural_document(
        self, kb_id: UUID, document: StructuralGraphDocument
    ) -> tuple[int, int]:
        return await self._run_async(self._store_structural_document_sync, kb_id, document)

    async def store_parent_mentions(
        self, kb_id: UUID, parent_chunk_id: str, graph: ExtractedGraph
    ) -> tuple[int, int]:
        return await self._run_async(
            self._store_parent_mentions_sync, kb_id, parent_chunk_id, graph
        )

    async def query_subgraph(self, kb_id: UUID, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return await self._run_async(self._query_subgraph_sync, kb_id, query, top_k)

    async def query_hybrid(
        self,
        kb_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
        candidate_k: int = 50,
        source_types: list[str] | None = None,
        time_from: float | None = None,
        time_to: float | None = None,
        document_id: UUID | None = None,
    ) -> list[HybridSearchResult]:
        return await self._run_async(
            self._query_hybrid_sync,
            kb_id,
            query_embedding,
            top_k,
            candidate_k,
            source_types,
            time_from,
            time_to,
            document_id,
        )

    def _delete_document_subgraph_sync(self, kb_id: UUID, document_id: UUID) -> None:
        graph_handle = self._client.select_graph(self._get_graph_name(kb_id))
        doc_id_str = str(document_id)
        query = (
            "MATCH (d:Document {id: $doc_id}) "
            "OPTIONAL MATCH (d)-[:HAS_PARENT]->(p:ParentChunk) "
            "OPTIONAL MATCH (p)-[:CONTAINS_CHILD]->(c:ChildChunk) "
            "DETACH DELETE d, p, c"
        )
        try:
            graph_handle.query(query, {"doc_id": doc_id_str})
        except Exception as e:
            logger.warning(
                "Failed to delete document subgraph for doc %s in FalkorDB: %s", doc_id_str, e
            )

    def _delete_graph_sync(self, kb_id: UUID) -> None:
        graph_name = self._get_graph_name(kb_id)
        try:
            graph_handle = self._client.select_graph(graph_name)
            graph_handle.delete()
        except Exception as e:
            logger.warning("Failed to delete graph %s in FalkorDB: %s", graph_name, e)

    async def delete_document_subgraph(self, kb_id: UUID, document_id: UUID) -> None:
        await self._run_async(self._delete_document_subgraph_sync, kb_id, document_id)

    async def delete_graph(self, kb_id: UUID) -> None:
        await self._run_async(self._delete_graph_sync, kb_id)
