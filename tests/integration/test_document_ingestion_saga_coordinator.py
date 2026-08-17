import tempfile
from unittest.mock import AsyncMock

import pytest

from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.modules.knowledge.application.sagas.document_ingestion_saga_coordinator import (
    DocumentIngestionSagaCoordinator,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.ontology import (
    NodeTypeDefinition,
    OntologySchema,
    PropertyDefinition,
    PropertyType,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.infrastructure.adapters.in_memory_embedding_service import (
    InMemoryEmbeddingService,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_graph_and_vector_store import (
    InMemoryGraphAndVectorStore,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.markitdown_document_parser import (
    MarkItDownDocumentParser,
)
from src.modules.knowledge.infrastructure.chunking.markdown_parent_child_chunker import (
    MarkdownParentChildChunker,
)
from src.modules.knowledge.infrastructure.extractors.structured_pydantic_graph_extractor import (
    StructuredPydanticGraphExtractor,
)


@pytest.fixture
def sample_ontology() -> OntologySchema:
    return OntologySchema(
        name="EnterpriseOntology",
        description="Ontologia corporativa",
        node_types=[
            NodeTypeDefinition(
                name="Service",
                description="Serviço de backend",
                properties=[
                    PropertyDefinition(
                        name="name",
                        type=PropertyType.STRING,
                        required=True,
                    )
                ],
            )
        ],
        relationship_types=[],
    )


@pytest.mark.asyncio
async def test_saga_coordinator_e2e_with_chunking_and_embeddings(
    sample_ontology: OntologySchema,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository()
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        parser = MarkItDownDocumentParser()
        chunker = MarkdownParentChildChunker(max_parent_tokens=100)
        embedding_service = InMemoryEmbeddingService(dimension=768)
        extractor = StructuredPydanticGraphExtractor()
        graph_and_vector = InMemoryGraphAndVectorStore()

        _ = DocumentIngestionSagaCoordinator(
            event_bus=bus,
            event_store=store,
            kb_repository=repo,
            storage=storage,
            parser=parser,
            extractor=extractor,
            graph_store=graph_and_vector,
            vector_store=graph_and_vector,
            chunker=chunker,
            embedding_service=embedding_service,
        )

        # 1. Create KB Aggregate and persist
        kb = KnowledgeBaseAggregate.create(
            name="EnterpriseKB",
            description="Base de conhecimento",
            ontology=sample_ontology,
        )
        await repo.save(kb)
        await store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=list(kb.uncommitted_events),
            expected_version=0,
        )
        kb.mark_events_as_committed()

        # 2. Attach Document and store bytes
        doc_id = kb.attach_document("guide.md", "text/markdown")
        doc_info = kb.documents[doc_id]
        raw_content = b"""# Cloud Architecture Guide
This guide explains Service payment and Service auth integration.

## Microservices
Details about the deployment infrastructure and scaling policies.
"""
        await storage.put_object(doc_info["storage_path"], raw_content, "text/markdown")
        kb.mark_document_stored(doc_id, doc_info["storage_path"], len(raw_content))

        # Publish uncommitted events to trigger the Saga
        uncommitted = list(kb.uncommitted_events)
        kb.mark_events_as_committed()
        await repo.save(kb)
        await store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=uncommitted,
            expected_version=1,
        )

        # 3. Verify final state
        updated_kb = await repo.get_by_id(kb.id)
        assert updated_kb is not None
        doc_state = updated_kb.documents[doc_id]
        assert doc_state["status"] == DocumentStatus.INDEXED
        assert doc_state["total_parents"] >= 2
        assert doc_state["total_children"] >= 2

        # 4. Verify vector search across chunks
        chunks = await graph_and_vector.search_similar_chunks(
            kb_id=kb.id,
            query_embedding=[0.0] * 768,
            top_k=5,
            document_ids=[doc_id],
        )
        assert len(chunks) >= 2
        assert all(c["document_id"] == doc_id for c in chunks)


@pytest.mark.asyncio
async def test_saga_coordinator_handles_chunking_failure(
    sample_ontology: OntologySchema,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository()
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        parser = MarkItDownDocumentParser()

        # Chunker that fails
        failing_chunker = AsyncMock(spec=MarkdownParentChildChunker)
        failing_chunker.chunk.side_effect = RuntimeError("Chunker syntax parsing error")

        embedding_service = InMemoryEmbeddingService(dimension=768)
        extractor = StructuredPydanticGraphExtractor()
        graph_and_vector = InMemoryGraphAndVectorStore()

        _ = DocumentIngestionSagaCoordinator(
            event_bus=bus,
            event_store=store,
            kb_repository=repo,
            storage=storage,
            parser=parser,
            extractor=extractor,
            graph_store=graph_and_vector,
            vector_store=graph_and_vector,
            chunker=failing_chunker,
            embedding_service=embedding_service,
        )

        kb = KnowledgeBaseAggregate.create("FailKB", "Desc", sample_ontology)
        await repo.save(kb)
        await store.append_events(kb.id, "KnowledgeBaseAggregate", list(kb.uncommitted_events), 0)
        kb.mark_events_as_committed()

        doc_id = kb.attach_document("doc.txt", "text/plain")
        doc_info = kb.documents[doc_id]
        raw_bytes = b"Some sample plain text"
        await storage.put_object(doc_info["storage_path"], raw_bytes, "text/plain")
        kb.mark_document_stored(doc_id, doc_info["storage_path"], len(raw_bytes))

        uncommitted = list(kb.uncommitted_events)
        kb.mark_events_as_committed()
        await repo.save(kb)
        await store.append_events(kb.id, "KnowledgeBaseAggregate", uncommitted, 1)

        updated_kb = await repo.get_by_id(kb.id)
        assert updated_kb is not None
        assert updated_kb.documents[doc_id]["status"] == DocumentStatus.FAILED
        assert updated_kb.documents[doc_id]["error"]["step"] == "MARKDOWN_CHUNKING"
