import tempfile
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.kernel.infrastructure.atomic_job_barrier import AtomicJobBarrier
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
from src.modules.knowledge.domain.interfaces.i_stream_job_queue import IStreamJobQueue
from src.modules.knowledge.domain.ontology import (
    NodeTypeDefinition,
    OntologySchema,
    PropertyDefinition,
    PropertyType,
)
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


@pytest.mark.asyncio
async def test_saga_coordinator_dispatches_to_stream() -> None:
    """
    Valida que ao receber DocumentChunkedEvent com stream_queue e barrier ativos,
    o coordenador despacha as tarefas para 'stream:jobs:graph' e inicializa a barreira.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository(event_bus=bus)
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

        mock_stream_queue = AsyncMock(spec=IStreamJobQueue)
        mock_barrier = AsyncMock(spec=AtomicJobBarrier)

        _coordinator = DocumentIngestionSagaCoordinator(
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
            stream_queue=mock_stream_queue,
            barrier=mock_barrier,
            run_in_background=False,
        )

        ontology = OntologySchema(
            name="TestOntology",
            description="Schema",
            node_types=[
                NodeTypeDefinition(
                    name="Concept",
                    description="Concept node",
                    properties=[
                        PropertyDefinition(
                            name="title",
                            type=PropertyType.STRING,
                            required=True,
                        )
                    ],
                )
            ],
            relationship_types=[],
        )

        kb = KnowledgeBaseAggregate.create(
            name="StreamKB",
            description="Base com despacho em streams",
            ontology=ontology,
        )
        await repo.save(kb)
        await store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=list(kb.uncommitted_events),
            expected_version=0,
        )
        kb.mark_events_as_committed()

        doc_id = uuid4()
        storage_path = f"{kb.storage_partition}/raw/{doc_id}-sample.md"
        doc = DocumentAggregate.create(
            document_id=doc_id,
            kb_id=kb.id,
            file_name="sample.md",
            content_type="text/markdown",
            storage_path=storage_path,
        )
        md_text = "# Header 1\nContent paragraph 1\n# Header 2\nContent paragraph 2"
        await storage.put_object(storage_path, md_text.encode("utf-8"), "text/markdown")
        doc.mark_stored(storage_path, len(md_text.encode("utf-8")))
        await doc_repo.save(doc)

        # Valida que a barreira foi inicializada para o documento
        mock_barrier.init_barrier.assert_awaited_once()
        call_args = mock_barrier.init_barrier.await_args
        assert call_args.args[0] == doc_id
        assert call_args.kwargs["step"] == "graph"

        # Valida que tarefas foram publicadas no stream 'stream:jobs:graph'
        assert mock_stream_queue.publish_task.await_count >= 1
        first_call = mock_stream_queue.publish_task.await_args_list[0]
        assert first_call.args[0] == "stream:jobs:graph"
        job_task = first_call.args[1]
        assert job_task.queue_name == "stream:jobs:graph"
