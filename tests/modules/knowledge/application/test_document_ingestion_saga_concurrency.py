import asyncio
import tempfile
from typing import Any

import pytest

from src.kernel.domain.domain_error import DomainError
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
from src.modules.knowledge.infrastructure.chunking.structure_tolerant_markdown_chunker import (
    StructureTolerantMarkdownChunker,
)
from src.modules.knowledge.infrastructure.extractors.structured_pydantic_graph_extractor import (
    StructuredPydanticGraphExtractor,
)


@pytest.fixture
def sample_ontology() -> OntologySchema:
    return OntologySchema(
        name="ConcurrencyTestOntology",
        description="Ontologia para teste de concorrência",
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
async def test_concurrent_document_ingestion_completes_all_documents(
    sample_ontology: OntologySchema,
) -> None:
    """
    Valida que múltiplos documentos disparados concorrentemente na mesma KB
    completam o pipeline até INDEXED sem serem abortados por colisão de versão.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository()
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        parser = ParallelVlmDocumentParser()
        chunker = StructureTolerantMarkdownChunker(
            max_parent_tokens=20,
            child_chunk_tokens=10,
            child_overlap_tokens=2,
        )
        embedding_service = InMemoryEmbeddingService(dimension=768)
        extractor = StructuredPydanticGraphExtractor()
        graph_store = InMemoryGraphStore()

        coordinator = DocumentIngestionSagaCoordinator(
            event_bus=bus,
            event_store=store,
            kb_repository=repo,
            storage=storage,
            parser=parser,
            extractor=extractor,
            graph_store=graph_store,
            chunker=chunker,
            embedding_service=embedding_service,
            run_in_background=True,
        )

        kb = KnowledgeBaseAggregate.create(
            name="ConcurrentKB",
            description="Base com múltiplos arquivos concorrentes",
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

        doc_count = 5
        doc_ids = []
        for i in range(doc_count):
            doc_id = kb.attach_document(f"doc_{i}.md", "text/markdown")
            doc_ids.append(doc_id)
            doc_info = kb.documents[doc_id]
            content = f"# Document {i}\nThis describes Service backend_{i} integration in detail.\n"
            content_bytes = content.encode("utf-8")
            await storage.put_object(doc_info["storage_path"], content_bytes, "text/markdown")
            kb.mark_document_stored(doc_id, doc_info["storage_path"], len(content_bytes))

        # Commita os eventos de anexo e upload de todos os docs
        uncommitted = list(kb.uncommitted_events)
        kb.mark_events_as_committed()
        await repo.save(kb)
        await store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=uncommitted,
            expected_version=1,
        )

        # Aguarda a conclusão de todas as background tasks da saga
        timeout = 10.0
        start = asyncio.get_event_loop().time()
        while coordinator._background_tasks and (asyncio.get_event_loop().time() - start) < timeout:
            await asyncio.sleep(0.05)

        updated_kb = await repo.get_by_id(kb.id)
        assert updated_kb is not None

        for doc_id in doc_ids:
            doc_state = updated_kb.documents.get(doc_id)
            assert doc_state is not None
            assert doc_state["status"] == DocumentStatus.INDEXED
            assert doc_state["total_parents"] >= 1
            assert doc_state["total_children"] >= 1


@pytest.mark.asyncio
async def test_optimistic_retry_recovers_from_injected_concurrency_conflict(
    sample_ontology: OntologySchema,
) -> None:
    """
    Injeta DomainError('Concurrency conflict') nas primeiras tentativas de gravação
    e valida que _execute_atomic_aggregate_mutation tenta novamente e tem sucesso.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository()
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        parser = ParallelVlmDocumentParser()
        chunker = StructureTolerantMarkdownChunker()
        embedding_service = InMemoryEmbeddingService()
        extractor = StructuredPydanticGraphExtractor()
        graph_store = InMemoryGraphStore()

        coordinator = DocumentIngestionSagaCoordinator(
            event_bus=bus,
            event_store=store,
            kb_repository=repo,
            storage=storage,
            parser=parser,
            extractor=extractor,
            graph_store=graph_store,
            chunker=chunker,
            embedding_service=embedding_service,
        )

        kb = KnowledgeBaseAggregate.create("RetryKB", "Desc", sample_ontology)
        await repo.save(kb)
        await store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=list(kb.uncommitted_events),
            expected_version=0,
        )
        kb.mark_events_as_committed()

        doc_id = kb.attach_document("retry_test.md", "text/markdown")
        kb.mark_document_stored(doc_id, "path", 100)
        await repo.save(kb)
        await store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=list(kb.uncommitted_events),
            expected_version=1,
        )
        kb.mark_events_as_committed()

        original_append = store.append_events
        call_count = 0

        async def flaking_append(
            aggregate_id: Any,
            aggregate_type: Any,
            events: Any,
            expected_version: Any,
        ) -> None:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # Simula conflito de concorrência nas duas primeiras tentativas
                raise DomainError(
                    f"Concurrency conflict: expected version {expected_version}, got 99",
                    code="CONCURRENCY_ERROR",
                )
            await original_append(aggregate_id, aggregate_type, events, expected_version)

        store.append_events = flaking_append  # type: ignore[method-assign]

        # Executa mutação que sofrerá 2 conflitos antes de ter sucesso na 3ª tentativa
        result_kb = await coordinator._execute_atomic_aggregate_mutation(
            kb_id=kb.id,
            mutate_fn=lambda fresh_kb: fresh_kb.mark_document_parsed(
                document_id=doc_id,
                markdown_storage_path="kb/parsed.md",
                markdown_preview="preview",
            ),
            max_retries=5,
        )

        assert call_count >= 3
        assert result_kb.documents[doc_id]["status"] in (
            DocumentStatus.PARSED,
            DocumentStatus.CHUNKED,
            DocumentStatus.INDEXED,
        )
