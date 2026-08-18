import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.ontology.node_type_definition import (
    NodeTypeDefinition,
)
from src.modules.knowledge.domain.ontology.ontology_template import OntologyTemplate
from src.modules.knowledge.domain.ontology.property_definition import PropertyDefinition
from src.modules.knowledge.domain.ontology.property_type import PropertyType
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.domain.value_objects.knowledge_base_status import (
    KnowledgeBaseStatus,
)
from src.modules.knowledge.infrastructure.adapters.postgres_knowledge_base_repository import (
    PostgresKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.postgres_ontology_repository import (
    PostgresOntologyRepository,
)


@pytest.mark.asyncio
async def test_postgres_ontology_repository_save_and_get() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    repo = PostgresOntologyRepository(pool=mock_pool)

    ont_id = uuid4()
    node = NodeTypeDefinition(
        name="Processo",
        description="Processo judicial",
        properties=[PropertyDefinition(name="numero", type=PropertyType.STRING, required=True)],
    )
    rel = RelationshipTypeDefinition(
        name="TRAMITA_EM",
        description="Tramitação",
        source_node_type="Processo",
        target_node_type="Tribunal",
        properties=[],
    )
    ontology = OntologyTemplate(
        id=ont_id,
        name="OntologiaTeste",
        description="Descrição teste",
        version=1,
        node_types=[node],
        relationship_types=[rel],
    )

    # Save
    await repo.save(ontology)
    assert mock_conn.execute.await_count == 1

    # Get by ID
    mock_conn.fetchrow.return_value = {
        "id": ont_id,
        "name": "OntologiaTeste",
        "description": "Descrição teste",
        "version": 1,
        "node_types": json.dumps([node.model_dump()]),
        "relationship_types": json.dumps([rel.model_dump()]),
    }

    fetched = await repo.get_by_id(ont_id)
    assert fetched is not None
    assert fetched.id == ont_id
    assert fetched.name == "OntologiaTeste"
    assert len(fetched.node_types) == 1
    assert fetched.node_types[0].name == "Processo"
    assert len(fetched.relationship_types) == 1
    assert fetched.relationship_types[0].name == "TRAMITA_EM"

    # Get by ID None
    mock_conn.fetchrow.return_value = None
    not_found = await repo.get_by_id(uuid4())
    assert not_found is None

    # Get by name and version
    mock_conn.fetchrow.return_value = {
        "id": ont_id,
        "name": "OntologiaTeste",
        "description": "Descrição teste",
        "version": 1,
        "node_types": json.dumps([node.model_dump()]),
        "relationship_types": json.dumps([rel.model_dump()]),
    }
    by_name = await repo.get_by_name_and_version("OntologiaTeste", 1)
    assert by_name is not None
    assert by_name.id == ont_id

    # List all
    mock_conn.fetch.return_value = [
        {
            "id": ont_id,
            "name": "OntologiaTeste",
            "description": "Descrição teste",
            "version": 1,
            "node_types": json.dumps([node.model_dump()]),
            "relationship_types": json.dumps([rel.model_dump()]),
        }
    ]
    all_onts = await repo.list_all()
    assert len(all_onts) == 1
    assert all_onts[0].name == "OntologiaTeste"


@pytest.mark.asyncio
async def test_postgres_knowledge_base_repository_save_and_get() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    mock_tx = MagicMock()
    mock_tx.__aenter__ = AsyncMock(return_value=None)
    mock_tx.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction = MagicMock(return_value=mock_tx)

    repo = PostgresKnowledgeBaseRepository(pool=mock_pool)

    kb_id = uuid4()
    doc_id = uuid4()
    kb = KnowledgeBaseAggregate(id=kb_id)
    kb.name = "KB Teste"
    kb.description = "Desc teste"
    kb.storage_partition = f"kb-{kb_id}"
    kb.status = KnowledgeBaseStatus.ACTIVE
    kb.documents = {
        doc_id: {
            "id": doc_id,
            "file_name": "doc.pdf",
            "status": DocumentStatus.INDEXED,
            "storage_path": "kb-123/raw/doc.pdf",
        }
    }

    # Save
    await repo.save(kb)
    assert mock_conn.execute.await_count == 2

    # Get by ID
    mock_conn.fetchrow.return_value = {
        "id": kb_id,
        "name": "KB Teste",
        "description": "Desc teste",
        "status": "ACTIVE",
        "storage_partition": f"kb-{kb_id}",
    }
    mock_conn.fetch.return_value = [
        {
            "id": doc_id,
            "file_name": "doc.pdf",
            "status": "INDEXED",
            "storage_path": "kb-123/raw/doc.pdf",
        }
    ]

    fetched = await repo.get_by_id(kb_id)
    assert fetched is not None
    assert fetched.id == kb_id
    assert fetched.name == "KB Teste"
    assert fetched.status == KnowledgeBaseStatus.ACTIVE
    assert len(fetched.documents) == 1
    assert fetched.documents[doc_id]["file_name"] == "doc.pdf"
    assert fetched.documents[doc_id]["status"] == DocumentStatus.INDEXED

    # Get by ID None
    mock_conn.fetchrow.return_value = None
    assert await repo.get_by_id(uuid4()) is None

    # List all
    mock_conn.fetch.side_effect = [
        [
            {
                "id": kb_id,
                "name": "KB Teste",
                "description": "Desc teste",
                "status": "ACTIVE",
                "storage_partition": f"kb-{kb_id}",
            }
        ],
        [
            {
                "id": doc_id,
                "kb_id": kb_id,
                "file_name": "doc.pdf",
                "status": "INDEXED",
                "storage_path": "kb-123/raw/doc.pdf",
            }
        ],
    ]
    all_kbs = await repo.list_all()
    assert len(all_kbs) == 1
    assert all_kbs[0].id == kb_id

    # List all empty
    mock_conn.fetch.side_effect = None
    mock_conn.fetch.return_value = []
    empty_kbs = await repo.list_all()
    assert empty_kbs == []
