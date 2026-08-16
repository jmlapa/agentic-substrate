import asyncio
import re
from typing import Any
from uuid import UUID

from falkordb import FalkorDB

from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph


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

    async def store_graph(self, kb_id: UUID, graph: ExtractedGraph) -> tuple[int, int]:
        return await asyncio.to_thread(self._store_graph_sync, kb_id, graph)

    async def query_subgraph(self, kb_id: UUID, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._query_subgraph_sync, kb_id, query, top_k)
