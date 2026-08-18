from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.modules.knowledge.domain.events.document_attached_event import (
    DocumentAttachedEvent,
)
from src.modules.knowledge.domain.events.document_chunked_event import (
    DocumentChunkedEvent,
)
from src.modules.knowledge.domain.events.document_knowledge_indexed_event import (
    DocumentKnowledgeIndexedEvent,
)
from src.modules.knowledge.domain.events.document_parsed_to_markdown_event import (
    DocumentParsedToMarkdownEvent,
)
from src.modules.knowledge.domain.events.document_processing_failed_event import (
    DocumentProcessingFailedEvent,
)
from src.modules.knowledge.domain.events.document_stored_event import DocumentStoredEvent
from src.modules.knowledge.domain.events.graph_extracted_from_document_event import (
    GraphExtractedFromDocumentEvent,
)
from src.modules.knowledge.domain.events.knowledge_base_created_event import (
    KnowledgeBaseCreatedEvent,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.infrastructure.projections.knowledge_base_projector import (
    KnowledgeBaseProjector,
)


@pytest.mark.asyncio
async def test_knowledge_base_projector_lifecycle_events() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Retorna template de ontologia mockado para resolução de ontology_id
    ont_id = uuid4()
    mock_conn.fetchrow.return_value = {"id": ont_id}

    event_bus = InMemoryEventBus()
    projector = KnowledgeBaseProjector(pool=mock_pool, event_bus=event_bus)

    kb_id = uuid4()
    doc_id = uuid4()
    ontology = OntologySchema(
        name="TestOntology",
        description="Test description",
        node_types=[],
        relationship_types=[],
    )

    # 1. KnowledgeBaseCreatedEvent
    kb_created = KnowledgeBaseCreatedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        name="Test KB",
        description="Desc",
        ontology=ontology,
        storage_partition=f"kb-{kb_id}",
    )
    await event_bus.publish([kb_created])
    assert mock_conn.execute.called

    # 2. DocumentAttachedEvent
    doc_attached = DocumentAttachedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        file_name="paper.pdf",
        content_type="application/pdf",
        storage_path=f"kb-{kb_id}/raw/{doc_id}.pdf",
        enable_ocr=True,
        ocr_instructions="Preserve tables",
    )
    await event_bus.publish([doc_attached])

    # 3. DocumentStoredEvent
    doc_stored = DocumentStoredEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        storage_path=f"kb-{kb_id}/raw/{doc_id}.pdf",
        byte_size=1024,
    )
    await event_bus.publish([doc_stored])

    # 4. DocumentParsedToMarkdownEvent
    doc_parsed = DocumentParsedToMarkdownEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        markdown_storage_path=f"kb-{kb_id}/md/{doc_id}.md",
        markdown_preview="# Title",
    )
    await event_bus.publish([doc_parsed])

    # 5. DocumentChunkedEvent
    doc_chunked = DocumentChunkedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        total_parents=10,
        total_children=50,
    )
    await event_bus.publish([doc_chunked])

    # 6. GraphExtractedFromDocumentEvent
    graph_extracted = GraphExtractedFromDocumentEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        node_count=5,
        edge_count=4,
        extracted_graph=ExtractedGraph(nodes=[], edges=[]),
    )
    await event_bus.publish([graph_extracted])

    # 7. DocumentKnowledgeIndexedEvent
    doc_indexed = DocumentKnowledgeIndexedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        indexed_nodes_count=5,
        indexed_edges_count=4,
    )
    await event_bus.publish([doc_indexed])

    # 8. DocumentProcessingFailedEvent
    doc_failed = DocumentProcessingFailedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        step="INDEXING",
        error_message="DB connection error",
    )
    await event_bus.publish([doc_failed])

    # 9. Test Rebuild / Replay
    events = [kb_created, doc_attached, doc_stored, doc_chunked, doc_indexed]
    await projector.rebuild_projections_from_events(events)
