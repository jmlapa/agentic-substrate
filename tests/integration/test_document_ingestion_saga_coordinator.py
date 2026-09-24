import tempfile
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.modules.knowledge.application.sagas.document_ingestion_saga_coordinator import (
    DocumentIngestionSagaCoordinator,
)
from src.modules.knowledge.domain.aggregates.document_aggregate import (
    DocumentAggregate,
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
from src.modules.knowledge.infrastructure.adapters.in_memory_graph_store import (
    InMemoryGraphStore,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.parallel_vlm_document_parser import (
    ParallelVlmDocumentParser,
)
from src.modules.knowledge.infrastructure.adapters.postgres_document_repository import (
    PostgresDocumentRepository,
)
from src.modules.knowledge.infrastructure.chunking.structure_tolerant_markdown_chunker import (
    StructureTolerantMarkdownChunker,
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
        doc_repo = PostgresDocumentRepository(event_store=store)
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        parser = ParallelVlmDocumentParser()
        chunker = StructureTolerantMarkdownChunker(
            max_parent_tokens=15,
            child_chunk_tokens=10,
            child_overlap_tokens=2,
        )
        embedding_service = InMemoryEmbeddingService(dimension=768)
        extractor = StructuredPydanticGraphExtractor()
        graph_store = InMemoryGraphStore()

        _ = DocumentIngestionSagaCoordinator(
            event_bus=bus,
            event_store=store,
            kb_repository=repo,
            document_repo=doc_repo,
            storage=storage,
            parser=parser,
            extractor=extractor,
            graph_store=graph_store,
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
        doc_id = uuid4()
        storage_path = f"{kb.storage_partition}/raw/{doc_id}-guide.md"
        doc = DocumentAggregate.create(
            document_id=doc_id,
            kb_id=kb.id,
            file_name="guide.md",
            content_type="text/markdown",
            storage_path=storage_path,
        )
        raw_content = b"""# Cloud Architecture Guide
This guide explains Service payment and Service auth integration.

## Microservices
Details about the deployment infrastructure and scaling policies.
"""
        await storage.put_object(storage_path, raw_content, "text/markdown")
        doc.mark_stored(storage_path, len(raw_content))
        await doc_repo.save(doc)

        # 3. Verify final state
        updated_doc = await doc_repo.get_by_id(doc_id)
        assert updated_doc is not None
        assert updated_doc.status == DocumentStatus.INDEXED
        assert updated_doc.total_parents >= 2
        assert updated_doc.total_children >= 2

        # 4. Verify hybrid graph search across chunks
        results = await graph_store.query_hybrid(
            kb_id=kb.id,
            query_embedding=[0.0] * 768,
            top_k=5,
        )
        assert len(results) >= 2


@pytest.mark.asyncio
async def test_saga_coordinator_handles_chunking_failure(
    sample_ontology: OntologySchema,
) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository()
        doc_repo = PostgresDocumentRepository(event_store=store)
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        parser = ParallelVlmDocumentParser()

        # Chunker that fails
        failing_chunker = AsyncMock(spec=StructureTolerantMarkdownChunker)
        failing_chunker.chunk.side_effect = RuntimeError("Chunker syntax parsing error")

        embedding_service = InMemoryEmbeddingService(dimension=768)
        extractor = StructuredPydanticGraphExtractor()
        graph_store = InMemoryGraphStore()

        _ = DocumentIngestionSagaCoordinator(
            event_bus=bus,
            event_store=store,
            kb_repository=repo,
            document_repo=doc_repo,
            storage=storage,
            parser=parser,
            extractor=extractor,
            graph_store=graph_store,
            chunker=failing_chunker,
            embedding_service=embedding_service,
        )

        kb = KnowledgeBaseAggregate.create("FailKB", "Desc", sample_ontology)
        await repo.save(kb)
        await store.append_events(kb.id, "KnowledgeBaseAggregate", list(kb.uncommitted_events), 0)
        kb.mark_events_as_committed()

        doc_id = uuid4()
        storage_path = f"{kb.storage_partition}/raw/{doc_id}-doc.txt"
        doc = DocumentAggregate.create(
            document_id=doc_id,
            kb_id=kb.id,
            file_name="doc.txt",
            content_type="text/plain",
            storage_path=storage_path,
        )
        raw_bytes = b"Some sample plain text"
        await storage.put_object(storage_path, raw_bytes, "text/plain")
        doc.mark_stored(storage_path, len(raw_bytes))
        await doc_repo.save(doc)

        updated_doc = await doc_repo.get_by_id(doc_id)
        assert updated_doc is not None
        assert updated_doc.status == DocumentStatus.FAILED
        assert updated_doc.error_step == "MARKDOWN_CHUNKING"
