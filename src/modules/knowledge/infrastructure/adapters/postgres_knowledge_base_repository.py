from typing import Any
from uuid import UUID

import asyncpg
from pydantic import TypeAdapter

from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.ontology.node_type_definition import (
    NodeTypeDefinition,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.domain.value_objects.knowledge_base_status import (
    KnowledgeBaseStatus,
)


class PostgresKnowledgeBaseRepository(IKnowledgeBaseRepository):
    """
    Adaptador de persistência e consulta (Read Model CQRS) para agregados de Knowledge Base.
    Armazena o aggregate root e seus documentos associados em transações relacionais,
    e responde a consultas com JOINs nas ontologias e métricas completas dos documentos.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._node_types_adapter: TypeAdapter[list[NodeTypeDefinition]] = TypeAdapter(
            list[NodeTypeDefinition]
        )
        self._rel_types_adapter: TypeAdapter[list[RelationshipTypeDefinition]] = TypeAdapter(
            list[RelationshipTypeDefinition]
        )

    async def save(self, aggregate: KnowledgeBaseAggregate) -> None:
        kb_query = """
        INSERT INTO knowledge_bases (
            id, name, description, status, storage_partition, ontology_id, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            status = EXCLUDED.status,
            storage_partition = EXCLUDED.storage_partition,
            ontology_id = COALESCE(EXCLUDED.ontology_id, knowledge_bases.ontology_id),
            updated_at = NOW();
        """

        status_str = (
            aggregate.status.value
            if isinstance(aggregate.status, KnowledgeBaseStatus)
            else str(aggregate.status)
        )

        async with self._pool.acquire() as conn:
            # Resolução de ontology_id
            ontology_id: UUID | None = None
            if aggregate.ontology and aggregate.ontology.name:
                row = await conn.fetchrow(
                    "SELECT id FROM ontology_templates WHERE name = $1 LIMIT 1",
                    aggregate.ontology.name,
                )
                if row:
                    ontology_id = row["id"]

            await conn.execute(
                kb_query,
                aggregate.id,
                aggregate.name,
                aggregate.description,
                status_str,
                aggregate.storage_partition,
                ontology_id,
            )

    async def get_by_id(self, id: UUID) -> KnowledgeBaseAggregate | None:
        kb_query = """
        SELECT
            kb.id,
            kb.name,
            kb.description,
            kb.status,
            kb.storage_partition,
            kb.ontology_id,
            ot.name AS ontology_name,
            ot.description AS ontology_description,
            ot.node_types AS ontology_node_types,
            ot.relationship_types AS ontology_rel_types
        FROM knowledge_bases kb
        LEFT JOIN ontology_templates ot ON kb.ontology_id = ot.id
        WHERE kb.id = $1;
        """
        doc_query = """
        SELECT
            id,
            file_name,
            status,
            storage_path,
            enable_ocr,
            ocr_instructions,
            total_parents,
            total_children,
            indexed_nodes_count,
            indexed_edges_count,
            progress_step,
            progress_current,
            progress_total,
            progress_percentage,
            progress_message,
            error_step,
            error_message
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
        SELECT
            kb.id,
            kb.name,
            kb.description,
            kb.status,
            kb.storage_partition,
            kb.ontology_id,
            ot.name AS ontology_name,
            ot.description AS ontology_description,
            ot.node_types AS ontology_node_types,
            ot.relationship_types AS ontology_rel_types
        FROM knowledge_bases kb
        LEFT JOIN ontology_templates ot ON kb.ontology_id = ot.id
        ORDER BY kb.created_at DESC;
        """
        doc_query = """
        SELECT
            id,
            kb_id,
            file_name,
            status,
            storage_path,
            enable_ocr,
            ocr_instructions,
            total_parents,
            total_children,
            indexed_nodes_count,
            indexed_edges_count,
            progress_step,
            progress_current,
            progress_total,
            progress_percentage,
            progress_message,
            error_step,
            error_message
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

    async def delete_by_id(self, id: UUID) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM attached_documents WHERE kb_id = $1;", id)
                await conn.execute("DELETE FROM knowledge_bases WHERE id = $1;", id)

    async def delete_document(self, kb_id: UUID, document_id: UUID) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM attached_documents WHERE id = $1 AND kb_id = $2;",
                document_id,
                kb_id,
            )

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

        # Reconstrói schema ontológico se a relação existir
        ontology_name = _get_val(kb_row, "ontology_name")
        if ontology_name:
            raw_nodes = _get_val(kb_row, "ontology_node_types")
            raw_rels = _get_val(kb_row, "ontology_rel_types")
            node_types = (
                self._node_types_adapter.validate_json(raw_nodes)
                if isinstance(raw_nodes, str)
                else self._node_types_adapter.validate_python(raw_nodes)
            )
            rel_types = (
                self._rel_types_adapter.validate_json(raw_rels)
                if isinstance(raw_rels, str)
                else self._rel_types_adapter.validate_python(raw_rels)
            )

            kb.ontology = OntologySchema(
                name=ontology_name,
                description=_get_val(kb_row, "ontology_description", "") or "",
                node_types=node_types,
                relationship_types=rel_types,
            )

        documents: dict[UUID, dict[str, Any]] = {}
        for d in doc_rows:
            try:
                st = DocumentStatus(_get_val(d, "status", "PENDING_UPLOAD"))
            except ValueError:
                st = DocumentStatus.PENDING_UPLOAD

            doc_dict: dict[str, Any] = {
                "id": _get_val(d, "id"),
                "file_name": _get_val(d, "file_name", "document"),
                "status": st,
                "storage_path": _get_val(d, "storage_path", ""),
                "enable_ocr": _get_val(d, "enable_ocr", False),
                "ocr_instructions": _get_val(d, "ocr_instructions"),
                "total_parents": _get_val(d, "total_parents"),
                "total_children": _get_val(d, "total_children"),
                "indexed_nodes_count": _get_val(d, "indexed_nodes_count", 0),
                "indexed_edges_count": _get_val(d, "indexed_edges_count", 0),
                "progress_step": _get_val(d, "progress_step"),
                "progress_current": _get_val(d, "progress_current", 0),
                "progress_total": _get_val(d, "progress_total", 0),
                "progress_percentage": _get_val(d, "progress_percentage", 0),
                "progress_message": _get_val(d, "progress_message"),
            }
            err_step = _get_val(d, "error_step")
            err_msg = _get_val(d, "error_message")
            if err_step and err_msg:
                doc_dict["error"] = {
                    "step": err_step,
                    "message": err_msg,
                    "error_message": err_msg,
                }

            documents[d["id"]] = doc_dict

        kb.documents = documents
        return kb


def _get_val(record: Any, key: str, default: Any = None) -> Any:
    if hasattr(record, "get"):
        val = record.get(key, default)
        return default if val is None and default is not None else val
    try:
        val = record[key]
        return default if val is None and default is not None else val
    except (KeyError, IndexError, TypeError):
        return default
