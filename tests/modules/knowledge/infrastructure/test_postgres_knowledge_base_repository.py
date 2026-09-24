from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.domain.value_objects.knowledge_base_status import (
    KnowledgeBaseStatus,
)
from src.modules.knowledge.infrastructure.adapters.postgres_knowledge_base_repository import (
    PostgresKnowledgeBaseRepository,
)


@pytest.mark.asyncio
async def test_save_executes_single_query_in_o1() -> None:
    """Verifica que save() não itera sobre attached_documents nem gera queries N+1."""
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Mock fetchrow para resolução de ontologia
    mock_conn.fetchrow.return_value = {"id": uuid4()}

    repo = PostgresKnowledgeBaseRepository(pool=mock_pool)

    kb = KnowledgeBaseAggregate(id=uuid4())
    kb.name = "Test KB"
    kb.description = "Test Desc"
    kb.storage_partition = f"kb-{kb.id}"
    kb.status = KnowledgeBaseStatus.ACTIVE
    kb.ontology = OntologySchema(
        name="TechOntology",
        description="Tech",
        node_types=[],
        relationship_types=[],
    )

    # Adiciona 50 documentos fictícios à KB
    for _ in range(50):
        d_id = uuid4()
        kb.documents[d_id] = {
            "id": d_id,
            "file_name": "file.pdf",
            "status": DocumentStatus.UPLOADED,
        }

    await repo.save(kb)

    # Verificação crucial: conn.execute foi chamado EXATAMENTE 1 vez
    # (apenas na tabela knowledge_bases)
    assert mock_conn.execute.call_count == 1
    args, _ = mock_conn.execute.call_args
    assert "INSERT INTO knowledge_bases" in args[0]
    assert "attached_documents" not in args[0]


@pytest.mark.asyncio
async def test_get_by_id_reconstructs_kb_and_documents() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    kb_id = uuid4()
    doc_id = uuid4()

    mock_conn.fetchrow.return_value = {
        "id": kb_id,
        "name": "Architecture KB",
        "description": "System architecture docs",
        "status": "ACTIVE",
        "storage_partition": f"kb-{kb_id}",
        "ontology_id": None,
        "ontology_name": None,
        "ontology_description": None,
        "ontology_node_types": None,
        "ontology_rel_types": None,
    }

    mock_conn.fetch.return_value = [
        {
            "id": doc_id,
            "kb_id": kb_id,
            "file_name": "arch.pdf",
            "status": "INDEXED",
            "storage_path": f"kb-{kb_id}/raw/{doc_id}-arch.pdf",
            "enable_ocr": True,
            "ocr_instructions": "Preserve tables",
            "total_parents": 10,
            "total_children": 50,
            "indexed_nodes_count": 25,
            "indexed_edges_count": 30,
            "progress_step": "INDEXED",
            "progress_current": 1,
            "progress_total": 1,
            "progress_percentage": 100,
            "progress_message": "Done",
            "error_step": None,
            "error_message": None,
        }
    ]

    repo = PostgresKnowledgeBaseRepository(pool=mock_pool)
    result = await repo.get_by_id(kb_id)

    assert result is not None
    assert result.id == kb_id
    assert result.name == "Architecture KB"
    assert result.status == KnowledgeBaseStatus.ACTIVE
    assert doc_id in result.documents
    assert result.documents[doc_id]["status"] == DocumentStatus.INDEXED
    assert result.documents[doc_id]["total_parents"] == 10
    assert result.documents[doc_id]["indexed_nodes_count"] == 25


@pytest.mark.asyncio
async def test_delete_by_id_executes_relational_deletes() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Setup async context manager for transaction
    mock_trans = MagicMock()
    mock_trans.__aenter__ = AsyncMock(return_value=None)
    mock_trans.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction = MagicMock(return_value=mock_trans)

    repo = PostgresKnowledgeBaseRepository(pool=mock_pool)
    kb_id = uuid4()
    await repo.delete_by_id(kb_id)

    assert mock_conn.execute.call_count == 2
    executed_queries = [call[0][0] for call in mock_conn.execute.call_args_list]
    assert any("DELETE FROM attached_documents" in q for q in executed_queries)
    assert any("DELETE FROM knowledge_bases" in q for q in executed_queries)


@pytest.mark.asyncio
async def test_delete_document_executes_target_delete() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    repo = PostgresKnowledgeBaseRepository(pool=mock_pool)
    kb_id = uuid4()
    doc_id = uuid4()
    await repo.delete_document(kb_id=kb_id, document_id=doc_id)

    mock_conn.execute.assert_awaited_once_with(
        "DELETE FROM attached_documents WHERE id = $1 AND kb_id = $2;",
        doc_id,
        kb_id,
    )
