from typing import Any
from uuid import UUID

import asyncpg

from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.domain.value_objects.knowledge_base_status import (
    KnowledgeBaseStatus,
)


class PostgresKnowledgeBaseRepository(IKnowledgeBaseRepository):
    """
    Adaptador de persistência para agregados de Knowledge Base no PostgreSQL.
    Armazena o aggregate root e seus documentos associados em transações relacionais.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save(self, aggregate: KnowledgeBaseAggregate) -> None:
        kb_query = """
        INSERT INTO knowledge_bases (
            id, name, description, status, storage_partition, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            status = EXCLUDED.status,
            storage_partition = EXCLUDED.storage_partition,
            updated_at = NOW();
        """

        doc_query = """
        INSERT INTO attached_documents (
            id, kb_id, file_name, status, storage_path, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            file_name = EXCLUDED.file_name,
            status = EXCLUDED.status,
            storage_path = EXCLUDED.storage_path,
            updated_at = NOW();
        """

        status_str = (
            aggregate.status.value
            if isinstance(aggregate.status, KnowledgeBaseStatus)
            else str(aggregate.status)
        )

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    kb_query,
                    aggregate.id,
                    aggregate.name,
                    aggregate.description,
                    status_str,
                    aggregate.storage_partition,
                )

                for doc_id, doc_info in aggregate.documents.items():
                    doc_status_raw = doc_info.get("status", DocumentStatus.PENDING_UPLOAD)
                    doc_status_str = (
                        doc_status_raw.value
                        if isinstance(doc_status_raw, DocumentStatus)
                        else str(doc_status_raw)
                    )
                    await conn.execute(
                        doc_query,
                        doc_id,
                        aggregate.id,
                        doc_info.get("file_name", "document"),
                        doc_status_str,
                        doc_info.get("storage_path", ""),
                    )

    async def get_by_id(self, id: UUID) -> KnowledgeBaseAggregate | None:
        kb_query = """
        SELECT id, name, description, status, storage_partition
        FROM knowledge_bases
        WHERE id = $1;
        """
        doc_query = """
        SELECT id, file_name, status, storage_path
        FROM attached_documents
        WHERE kb_id = $1
        ORDER BY created_at ASC;
        """

        async with self._pool.acquire() as conn:
            kb_row = await conn.fetchrow(kb_query, id)
            if not kb_row:
                return None

            doc_rows = await conn.fetch(doc_query, id)
            return self._build_aggregate(kb_row, doc_rows)

    async def list_all(self) -> list[KnowledgeBaseAggregate]:
        kb_query = """
        SELECT id, name, description, status, storage_partition
        FROM knowledge_bases
        ORDER BY created_at DESC;
        """
        doc_query = """
        SELECT id, kb_id, file_name, status, storage_path
        FROM attached_documents
        ORDER BY created_at ASC;
        """

        async with self._pool.acquire() as conn:
            kb_rows = await conn.fetch(kb_query)
            if not kb_rows:
                return []

            doc_rows = await conn.fetch(doc_query)
            docs_by_kb: dict[UUID, list[asyncpg.Record]] = {}
            for d in doc_rows:
                docs_by_kb.setdefault(d["kb_id"], []).append(d)

            aggregates: list[KnowledgeBaseAggregate] = []
            for kb_row in kb_rows:
                kb_docs = docs_by_kb.get(kb_row["id"], [])
                aggregates.append(self._build_aggregate(kb_row, kb_docs))

            return aggregates

    def _build_aggregate(
        self, kb_row: asyncpg.Record, doc_rows: list[asyncpg.Record]
    ) -> KnowledgeBaseAggregate:
        kb = KnowledgeBaseAggregate(id=kb_row["id"])
        kb.name = kb_row["name"]
        kb.description = kb_row["description"] or ""
        kb.storage_partition = kb_row["storage_partition"]

        try:
            kb.status = KnowledgeBaseStatus(kb_row["status"])
        except ValueError:
            kb.status = KnowledgeBaseStatus.ACTIVE

        documents: dict[UUID, dict[str, Any]] = {}
        for d in doc_rows:
            try:
                st = DocumentStatus(d["status"])
            except ValueError:
                st = DocumentStatus.PENDING_UPLOAD

            documents[d["id"]] = {
                "id": d["id"],
                "file_name": d["file_name"],
                "status": st,
                "storage_path": d["storage_path"],
            }

        kb.documents = documents
        return kb
