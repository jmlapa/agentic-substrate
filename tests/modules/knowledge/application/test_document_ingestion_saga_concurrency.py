import asyncio
import tempfile
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
    completam o pipeline até INDEXED sem colisões de versão no Event Store.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository()
        doc_repo = PostgresDocumentRepository(event_store=store)
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
            document_repo=doc_repo,
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
        docs: list[DocumentAggregate] = []
        for i in range(doc_count):
            doc_id = uuid4()
            file_name = f"doc_{i}.md"
            storage_path = f"{kb.storage_partition}/raw/{doc_id}-{file_name}"
            content = f"# Document {i}\nThis describes Service backend_{i} integration in detail.\n"
            content_bytes = content.encode("utf-8")
            await storage.put_object(storage_path, content_bytes, "text/markdown")

            doc = DocumentAggregate.create(
                document_id=doc_id,
                kb_id=kb.id,
                file_name=file_name,
                content_type="text/markdown",
                storage_path=storage_path,
            )
            doc.mark_stored(storage_path, len(content_bytes))
            docs.append(doc)

        # Salva todos os documentos concorrentemente
        await asyncio.gather(*(doc_repo.save(doc) for doc in docs))

        # Aguarda a conclusão de todas as background tasks da saga
        timeout = 15.0
        start = asyncio.get_event_loop().time()
        while coordinator._background_tasks and (asyncio.get_event_loop().time() - start) < timeout:
            await asyncio.sleep(0.05)

        for doc in docs:
            saved_doc = await doc_repo.get_by_id(doc.id)
            assert saved_doc is not None
            assert saved_doc.status == DocumentStatus.INDEXED
            assert saved_doc.total_parents >= 1
            assert saved_doc.total_children >= 1


@pytest.mark.asyncio
async def test_sovereign_document_streams_prevent_concurrency_collisions(
    sample_ontology: OntologySchema,
) -> None:
    """
    Valida que documentos distintos processando em paralelo possuem streams unitários
    separados no Event Store e operam com zero conflito de concorrência.
    """
    with tempfile.TemporaryDirectory():
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository()
        doc_repo = PostgresDocumentRepository(event_store=store)

        kb = KnowledgeBaseAggregate.create("IsolatedStreamsKB", "Desc", sample_ontology)
        await repo.save(kb)

        # Cria 10 documentos independentes na mesma KB
        docs = [
            DocumentAggregate.create(
                document_id=uuid4(),
                kb_id=kb.id,
                file_name=f"file_{i}.txt",
                content_type="text/plain",
                storage_path=f"{kb.storage_partition}/raw/file_{i}.txt",
            )
            for i in range(10)
        ]

        # Simula mutações concorrentes em todos os 10 documentos simultaneamente
        async def mutate_doc(doc: DocumentAggregate) -> None:
            doc.mark_stored(doc.storage_path, 100)
            doc.mark_parsed(f"md_{doc.id}", "preview")
            doc.mark_chunked(total_parents=2, total_children=4)
            await doc_repo.save(doc)

        # Todas as mutações paralelas devem executar sem conflito de concorrência
        await asyncio.gather(*(mutate_doc(d) for d in docs))

        for doc in docs:
            loaded = await doc_repo.get_by_id(doc.id)
            assert loaded is not None
            assert loaded.status == DocumentStatus.CHUNKED
            assert loaded.total_parents == 2
            assert loaded.total_children == 4
