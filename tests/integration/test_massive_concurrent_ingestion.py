from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
import redis.asyncio as aioredis

from src.kernel.infrastructure.atomic_job_barrier import AtomicJobBarrier
from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.kernel.infrastructure.redis_stream_job_queue import RedisStreamJobQueue
from src.modules.knowledge.application.sagas.document_ingestion_saga_coordinator import (
    DocumentIngestionSagaCoordinator,
)
from src.modules.knowledge.application.workers.graph_job_worker import GraphJobWorker
from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.interfaces.i_graph_extractor import IGraphExtractor
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.ontology import (
    NodeTypeDefinition,
    OntologySchema,
    PropertyDefinition,
    PropertyType,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.domain.value_objects.job_task import JobTask
from src.modules.knowledge.domain.value_objects.parent_graph_job_payload import (
    ParentGraphJobPayload,
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
from src.modules.knowledge.infrastructure.adapters.parent_graph_checkpoint_storage import (
    ParentGraphCheckpointStorage,
)
from src.modules.knowledge.infrastructure.adapters.postgres_document_repository import (
    PostgresDocumentRepository,
)
from src.modules.knowledge.infrastructure.chunking.structure_tolerant_markdown_chunker import (
    StructureTolerantMarkdownChunker,
)


class FastMockGraphExtractor(IGraphExtractor):
    async def extract_graph(
        self,
        markdown_text: str,
        ontology: OntologySchema,
        kb_id: UUID | None = None,
        max_retries: int = 3,
    ) -> ExtractedGraph:
        # Extração simulada instantânea
        node = GraphNode(
            id=f"node_{uuid4().hex[:6]}",
            node_type="Entity",
            properties={"text": markdown_text[:30]},
        )
        return ExtractedGraph(nodes=[node], edges=[])


@pytest.fixture
async def redis_client() -> AsyncIterator[aioredis.Redis[bytes]]:
    client: aioredis.Redis[bytes] = aioredis.from_url(
        "redis://localhost:6381/0", decode_responses=False
    )
    yield client
    await getattr(client, "aclose", client.close)()


@pytest.mark.asyncio
async def test_massive_concurrent_ingestion_50_documents(
    redis_client: aioredis.Redis[bytes],
) -> None:
    """
    Submete 50 documentos concorrentemente na mesma Knowledge Base.
    Valida que:
    1. A coordenação distribuída via Redis Streams + AtomicJobBarrier não trava.
    2. Zero colisões de versão de eventos ou deadlocks entre os 50 documentos.
    3. Todos os 50 documentos atingem o estado INDEXED no DocumentAggregate em O(1).
    """
    group_name = "test_graph_workers"

    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        kb_repo = InMemoryKnowledgeBaseRepository()
        doc_repo = PostgresDocumentRepository(event_store=store)
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        checkpoint_storage = ParentGraphCheckpointStorage(storage=storage)

        stream_queue = RedisStreamJobQueue(client=redis_client)
        barrier = AtomicJobBarrier(client=redis_client)

        parser = ParallelVlmDocumentParser()
        chunker = StructureTolerantMarkdownChunker(
            max_parent_tokens=50,
            child_chunk_tokens=25,
            child_overlap_tokens=5,
        )
        embedding_service = InMemoryEmbeddingService(dimension=768)
        extractor = FastMockGraphExtractor()
        graph_store: IGraphStore = InMemoryGraphStore()

        # Coordenador da saga configurado para despacho em Redis Streams
        coordinator = DocumentIngestionSagaCoordinator(
            event_bus=bus,
            event_store=store,
            kb_repository=kb_repo,
            storage=storage,
            parser=parser,
            extractor=extractor,
            graph_store=graph_store,
            chunker=chunker,
            embedding_service=embedding_service,
            parent_graph_checkpoint_storage=checkpoint_storage,
            document_repo=doc_repo,
            stream_queue=stream_queue,
            barrier=barrier,
            run_in_background=False,
        )

        ontology = OntologySchema(
            name="MassiveTestOntology",
            description="Schema para teste de concorrência massiva",
            node_types=[
                NodeTypeDefinition(
                    name="Entity",
                    description="Generic entity",
                    properties=[
                        PropertyDefinition(
                            name="text",
                            type=PropertyType.STRING,
                            required=True,
                        )
                    ],
                )
            ],
            relationship_types=[],
        )

        kb = KnowledgeBaseAggregate.create(
            name="MassiveKB",
            description="50 docs massivos",
            ontology=ontology,
        )
        await kb_repo.save(kb)
        await store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=list(kb.uncommitted_events),
            expected_version=0,
        )
        kb.mark_events_as_committed()

        stream_name = "stream:jobs:graph"
        # Garante stream limpo
        try:
            await redis_client.delete(stream_name)
        except Exception:
            pass

        # Worker autônomo consumindo do stream compartilhado
        worker = GraphJobWorker(
            stream_queue=stream_queue,
            storage=storage,
            checkpoint_storage=checkpoint_storage,
            barrier=barrier,
            graph_extractor=extractor,
            graph_store=graph_store,
            document_repo=doc_repo,
            stream_name=stream_name,
            group_name=group_name,
            consumer_name="massive-worker-1",
        )

        # Prepara 50 documentos
        doc_count = 50
        doc_aggregates: list[DocumentAggregate] = []

        for i in range(doc_count):
            doc_id = uuid4()
            file_name = f"doc_{i}.md"
            content = (
                f"# Title {i}\n"
                f"Section description for document {i} with valuable knowledge details.\n"
                f"## Subtitle {i}\n"
                f"Detailed body content for analysis and entity extraction.\n"
            )
            raw_path = f"{kb.storage_partition}/raw/{doc_id}/{file_name}"
            await storage.put_object(raw_path, content.encode("utf-8"), "text/markdown")

            doc_agg = DocumentAggregate.create(
                document_id=doc_id,
                kb_id=kb.id,
                file_name=file_name,
                content_type="text/markdown",
                storage_path=raw_path,
            )
            doc_agg.mark_stored(raw_path, len(content.encode("utf-8")))
            await doc_repo.save(doc_agg)
            doc_aggregates.append(doc_agg)

        # Inicia o worker em background
        await worker.start()

        # Dispara o processamento dos 50 documentos simultaneamente via saga
        async def _trigger_ingestion(d: DocumentAggregate) -> None:
            # Carrega o evento de upload emitido e envia para o saga coordinator
            events = await store.get_events(d.id)
            stored_event = next(e for e in events if e.event_type == "DocumentStoredEvent")
            await coordinator.handle_document_stored(stored_event)

        # Dispara todas as 50 requisições simultâneas
        await asyncio.gather(*[_trigger_ingestion(d) for d in doc_aggregates])

        # Aguarda todos os 50 documentos chegarem a INDEXED
        timeout = 15.0
        start_time = asyncio.get_event_loop().time()
        completed = False

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            all_indexed = True
            for d in doc_aggregates:
                latest_doc = await doc_repo.get_by_id(d.id)
                if latest_doc is None or latest_doc.status != DocumentStatus.INDEXED:
                    all_indexed = False
                    break
            if all_indexed:
                completed = True
                break
            await asyncio.sleep(0.1)

        await worker.stop()

        # Valida que todos os 50 documentos foram 100% indexados
        assert completed, "Nem todos os 50 documentos atingiram INDEXED no tempo limite"

        for d in doc_aggregates:
            final_doc = await doc_repo.get_by_id(d.id)
            assert final_doc is not None
            assert final_doc.status == DocumentStatus.INDEXED
            assert final_doc.total_parents >= 1
            assert final_doc.total_children >= 1
            assert final_doc.indexed_nodes_count >= 1


@pytest.mark.asyncio
async def test_worker_crash_and_xautoclaim_recovery(
    redis_client: aioredis.Redis[bytes],
) -> None:
    """
    Simula falha/queda súbita de worker durante extração e valida que:
    1. A tarefa não confirmada (PEL) é resgatada via claim_stale_tasks (XAUTOCLAIM).
    2. O novo worker recupera a tarefa, aproveita/gera checkpoints duráveis.
    3. A barreira atômica é completada e o documento atinge INDEXED.
    """
    stream_name = "stream:jobs:graph:crash_test"
    group_name = "crash_test_group"

    try:
        await redis_client.delete(stream_name)
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        doc_repo = PostgresDocumentRepository(event_store=store)
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        checkpoint_storage = ParentGraphCheckpointStorage(storage=storage)
        stream_queue = RedisStreamJobQueue(client=redis_client)
        barrier = AtomicJobBarrier(client=redis_client)
        extractor = FastMockGraphExtractor()
        graph_store: IGraphStore = InMemoryGraphStore()

        kb_id = uuid4()
        doc_id = uuid4()
        storage_partition = f"partition_{kb_id}"

        doc_agg = DocumentAggregate.create(
            document_id=doc_id,
            kb_id=kb_id,
            file_name="crash_test.md",
            content_type="text/markdown",
            storage_path=f"{storage_partition}/raw/{doc_id}/crash_test.md",
        )
        doc_agg.mark_stored(f"{storage_partition}/raw/{doc_id}/crash_test.md", 100)
        doc_agg.mark_chunked(total_parents=1, total_children=1)
        await doc_repo.save(doc_agg)

        await barrier.init_barrier(doc_id, total_chunks=1, step="graph")

        payload = ParentGraphJobPayload(
            kb_id=kb_id,
            document_id=doc_id,
            parent_id=f"{doc_id}-p1",
            parent_index=0,
            total_parents=1,
            header_path="Root",
            storage_partition=storage_partition,
            content="Crash test content",
        )
        task = JobTask(
            id=f"{doc_id}_{doc_id}-p1",
            queue_name=stream_name,
            payload=payload.model_dump(mode="json"),
        )
        await stream_queue.publish_task(stream_name, task)

        # Worker 1 lê a tarefa mas 'cai' (não processa nem dá ACK)
        worker_1_tasks = await stream_queue.consume_tasks(
            stream_name=stream_name,
            group_name=group_name,
            consumer_name="dying-worker-1",
            count=1,
            block_ms=1000,
        )
        assert len(worker_1_tasks) == 1
        msg_id, leaked_task = worker_1_tasks[0]
        assert leaked_task.id == task.id
        # Worker 1 morre aqui (nenhum ack_task é chamado)

        # Worker 2 inicializa e reinvindica tarefas órfãs via XAUTOCLAIM
        worker_2 = GraphJobWorker(
            stream_queue=stream_queue,
            storage=storage,
            checkpoint_storage=checkpoint_storage,
            barrier=barrier,
            graph_extractor=extractor,
            graph_store=graph_store,
            document_repo=doc_repo,
            stream_name=stream_name,
            group_name=group_name,
            consumer_name="survivor-worker-2",
        )

        # Reivindica explicitamente tarefas com idle >= 0ms
        claimed = await stream_queue.claim_stale_tasks(
            stream_name=stream_name,
            group_name=group_name,
            consumer_name="survivor-worker-2",
            min_idle_time_ms=0,
            count=10,
        )
        assert len(claimed) == 1
        claimed_msg_id, claimed_task = claimed[0]

        # Worker 2 processa a tarefa resgatada
        success = await worker_2.process_task(claimed_msg_id, claimed_task)
        assert success is True

        # Valida que o documento atingiu INDEXED com o nó extraído
        final_doc = await doc_repo.get_by_id(doc_id)
        assert final_doc is not None
        assert final_doc.status == DocumentStatus.INDEXED
        assert final_doc.indexed_nodes_count >= 1
