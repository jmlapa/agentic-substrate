from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.modules.knowledge.domain.events.document_chunked_event import (
    DocumentChunkedEvent,
)
from src.modules.knowledge.domain.events.document_knowledge_indexed_event import (
    DocumentKnowledgeIndexedEvent,
)
from src.modules.knowledge.domain.events.document_parsed_to_markdown_event import (
    DocumentParsedToMarkdownEvent,
)
from src.modules.knowledge.domain.events.document_progress_updated_event import (
    DocumentProgressUpdatedEvent,
)
from src.modules.knowledge.domain.events.graph_extracted_from_document_event import (
    GraphExtractedFromDocumentEvent,
)
from src.modules.knowledge.domain.value_objects.extracted_graph import (
    ExtractedGraph,
)
from src.modules.knowledge.infrastructure.projections.knowledge_base_projector import (
    KnowledgeBaseProjector,
)


@pytest.mark.asyncio
async def test_projector_handles_document_progress_updated_event() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    bus = InMemoryEventBus()
    _ = KnowledgeBaseProjector(pool=mock_pool, event_bus=bus)

    kb_id = uuid4()
    doc_id = uuid4()

    event = DocumentProgressUpdatedEvent(
        aggregate_id=kb_id,
        document_id=doc_id,
        step="OCR",
        current=142,
        total=437,
        percentage=32,
        message="Transcrevendo página 142 de 437",
    )

    await bus.publish([event])

    assert mock_conn.execute.called
    query_call = mock_conn.execute.call_args[0]
    sql = query_call[0]
    assert "UPDATE attached_documents" in sql
    assert "progress_step = $1" in sql
    assert query_call[1] == "OCR"
    assert query_call[2] == 142
    assert query_call[3] == 437
    assert query_call[4] == 32
    assert query_call[5] == "Transcrevendo página 142 de 437"
    assert query_call[6] == doc_id


@pytest.mark.asyncio
async def test_projector_handles_lifecycle_transitions_with_clean_progress() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    bus = InMemoryEventBus()
    _ = KnowledgeBaseProjector(pool=mock_pool, event_bus=bus)

    kb_id = uuid4()
    doc_id = uuid4()

    # 1. Parsed Event
    parsed_event = DocumentParsedToMarkdownEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        markdown_storage_path="path/to/md",
        markdown_preview="# Title\nPreview",
    )
    await bus.publish([parsed_event])
    sql = mock_conn.execute.call_args[0][0]
    assert "status = 'PARSED'" in sql
    assert "progress_step = 'CHUNKING'" in sql

    # 2. Chunked Event
    chunked_event = DocumentChunkedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        total_parents=10,
        total_children=50,
        chunks_summary=[],
    )
    await bus.publish([chunked_event])
    sql = mock_conn.execute.call_args[0][0]
    assert "status = 'CHUNKED'" in sql
    assert "progress_step = 'EMBEDDINGS'" in sql

    # 3. Graph Extracted Event
    graph_event = GraphExtractedFromDocumentEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        node_count=0,
        edge_count=0,
        extracted_graph=ExtractedGraph(nodes=[], edges=[]),
    )
    await bus.publish([graph_event])
    sql = mock_conn.execute.call_args[0][0]
    assert "status = 'GRAPH_EXTRACTED'" in sql
    assert "progress_step = 'INDEXING'" in sql

    # 4. Indexed Event
    indexed_event = DocumentKnowledgeIndexedEvent(
        aggregate_id=kb_id,
        aggregate_type="KnowledgeBaseAggregate",
        document_id=doc_id,
        indexed_nodes_count=25,
        indexed_edges_count=40,
    )
    await bus.publish([indexed_event])
    sql = mock_conn.execute.call_args[0][0]
    assert "status = 'INDEXED'" in sql
    assert "progress_percentage = 100" in sql
