import json
from typing import Any
from uuid import UUID

import asyncpg

from src.modules.knowledge.domain.interfaces.i_vector_store import IVectorStore
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph


class PgVectorStoreAdapter(IVectorStore):
    def __init__(
        self,
        pool: asyncpg.Pool,
        embedding_dimension: int = 1536,
    ) -> None:
        self._pool = pool
        self._embedding_dimension = embedding_dimension

    async def initialize_schema(self) -> None:
        query = f"""
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS node_embeddings (
            id VARCHAR(255) NOT NULL,
            kb_id UUID NOT NULL,
            node_type VARCHAR(255) NOT NULL,
            properties JSONB NOT NULL,
            embedding vector({self._embedding_dimension}),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (kb_id, id)
        );

        CREATE INDEX IF NOT EXISTS idx_node_embeddings_kb_id 
        ON node_embeddings (kb_id);
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query)

    async def store_node_embeddings(self, kb_id: UUID, graph: ExtractedGraph) -> int:
        if not graph.nodes:
            return 0

        records: list[tuple[str, UUID, str, str, str | None]] = []
        for node in graph.nodes:
            props_json = json.dumps(node.properties)
            # Embedding representation: if node has embedding in properties, use it;
            # otherwise placeholder or null vector string
            raw_emb = node.properties.get("_embedding")
            emb_str: str | None = None
            if isinstance(raw_emb, list):
                emb_str = f"[{','.join(str(float(x)) for x in raw_emb)}]"

            records.append(
                (
                    node.id,
                    kb_id,
                    node.node_type,
                    props_json,
                    emb_str,
                )
            )

        query = """
        INSERT INTO node_embeddings (id, kb_id, node_type, properties, embedding)
        VALUES ($1, $2, $3, $4::jsonb, $5::vector)
        ON CONFLICT (kb_id, id) DO UPDATE SET
            node_type = EXCLUDED.node_type,
            properties = EXCLUDED.properties,
            embedding = COALESCE(EXCLUDED.embedding, node_embeddings.embedding)
        """
        async with self._pool.acquire() as conn:
            await conn.executemany(query, records)

        return len(graph.nodes)

    async def search_similar_nodes(
        self, kb_id: UUID, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        emb_str = f"[{','.join(str(float(x)) for x in query_embedding)}]"
        query = """
        SELECT id, node_type, properties,
               1 - (embedding <=> $2::vector) AS score
        FROM node_embeddings
        WHERE kb_id = $1 AND embedding IS NOT NULL
        ORDER BY embedding <=> $2::vector
        LIMIT $3;
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, kb_id, emb_str, top_k)

        results: list[dict[str, Any]] = []
        for row in rows:
            props = row["properties"]
            if isinstance(props, str):
                props = json.loads(props)
            results.append(
                {
                    "id": row["id"],
                    "score": float(row["score"]) if row["score"] is not None else 0.0,
                    "node_type": row["node_type"],
                    "properties": props,
                }
            )
        return results
