import json
from typing import Any
from uuid import UUID

import asyncpg

from src.modules.knowledge.domain.interfaces.i_vector_store import IVectorStore
from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk


class PgVectorStoreAdapter(IVectorStore):
    def __init__(
        self,
        pool: asyncpg.Pool,
        embedding_dimension: int = 768,
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

        CREATE TABLE IF NOT EXISTS document_chunks (
            id VARCHAR(255) NOT NULL,
            kb_id UUID NOT NULL,
            document_id UUID NOT NULL,
            parent_chunk_id VARCHAR(255) NOT NULL,
            chunk_index INT NOT NULL,
            header_path VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            parent_content TEXT NOT NULL,
            embedding vector({self._embedding_dimension}),
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (kb_id, id)
        );

        CREATE INDEX IF NOT EXISTS idx_document_chunks_kb_doc 
        ON document_chunks (kb_id, document_id);

        CREATE INDEX IF NOT EXISTS idx_document_chunks_hnsw 
        ON document_chunks USING hnsw (embedding vector_cosine_ops);
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query)

    async def store_node_embeddings(self, kb_id: UUID, graph: ExtractedGraph) -> int:
        if not graph.nodes:
            return 0

        records: list[tuple[str, UUID, str, str, str | None]] = []
        for node in graph.nodes:
            props_json = json.dumps(node.properties)
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

    async def store_document_chunks(
        self,
        kb_id: UUID,
        document_id: UUID,
        chunks: list[ChildChunk],
        parent_chunks: list[ParentChunk] | None = None,
    ) -> int:
        if not chunks:
            return 0

        parent_map = {p.id: p.content for p in (parent_chunks or [])}
        records: list[tuple[str, UUID, UUID, str, int, str, str, str, str | None, str]] = []

        for chunk in chunks:
            emb_str: str | None = None
            if chunk.embedding is not None:
                emb_str = f"[{','.join(str(float(x)) for x in chunk.embedding)}]"

            meta_json = json.dumps(chunk.metadata)
            parent_content = parent_map.get(chunk.parent_chunk_id, "")

            records.append(
                (
                    chunk.id,
                    kb_id,
                    document_id,
                    chunk.parent_chunk_id,
                    chunk.chunk_index,
                    chunk.header_path,
                    chunk.content,
                    parent_content,
                    emb_str,
                    meta_json,
                )
            )

        query = """
        INSERT INTO document_chunks (
            id, kb_id, document_id, parent_chunk_id, chunk_index,
            header_path, content, parent_content, embedding, metadata
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector, $10::jsonb)
        ON CONFLICT (kb_id, id) DO UPDATE SET
            parent_chunk_id = EXCLUDED.parent_chunk_id,
            chunk_index = EXCLUDED.chunk_index,
            header_path = EXCLUDED.header_path,
            content = EXCLUDED.content,
            parent_content = EXCLUDED.parent_content,
            embedding = COALESCE(EXCLUDED.embedding, document_chunks.embedding),
            metadata = EXCLUDED.metadata
        """
        async with self._pool.acquire() as conn:
            await conn.executemany(query, records)

        return len(chunks)

    async def search_similar_chunks(
        self,
        kb_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
        document_ids: list[UUID] | None = None,
    ) -> list[dict[str, Any]]:
        emb_str = f"[{','.join(str(float(x)) for x in query_embedding)}]"

        if document_ids:
            query = """
            SELECT id, document_id, parent_chunk_id, chunk_index,
                   header_path, content, parent_content, metadata,
                   1 - (embedding <=> $2::vector) AS score
            FROM document_chunks
            WHERE kb_id = $1 AND document_id = ANY($4::uuid[]) AND embedding IS NOT NULL
            ORDER BY embedding <=> $2::vector
            LIMIT $3;
            """
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(query, kb_id, emb_str, top_k, document_ids)
        else:
            query = """
            SELECT id, document_id, parent_chunk_id, chunk_index,
                   header_path, content, parent_content, metadata,
                   1 - (embedding <=> $2::vector) AS score
            FROM document_chunks
            WHERE kb_id = $1 AND embedding IS NOT NULL
            ORDER BY embedding <=> $2::vector
            LIMIT $3;
            """
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(query, kb_id, emb_str, top_k)

        results: list[dict[str, Any]] = []
        for row in rows:
            meta = row["metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta)
            results.append(
                {
                    "id": row["id"],
                    "document_id": row["document_id"],
                    "score": float(row["score"]) if row["score"] is not None else 0.0,
                    "parent_chunk_id": row["parent_chunk_id"],
                    "chunk_index": row["chunk_index"],
                    "header_path": row["header_path"],
                    "content": row["content"],
                    "parent_content": row["parent_content"],
                    "metadata": meta,
                }
            )
        return results
