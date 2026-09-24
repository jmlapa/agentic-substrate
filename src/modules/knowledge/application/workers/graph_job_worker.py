import asyncio
import json
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import asyncpg

from src.kernel.application.event_bus import EventBus
from src.kernel.infrastructure.atomic_job_barrier import AtomicJobBarrier
from src.modules.knowledge.domain.interfaces.i_document_repository import (
    IDocumentRepository,
)
from src.modules.knowledge.domain.interfaces.i_graph_extractor import IGraphExtractor
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.domain.interfaces.i_stream_job_queue import IStreamJobQueue
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.domain.value_objects.job_task import JobTask
from src.modules.knowledge.domain.value_objects.parent_graph_job_payload import (
    ParentGraphJobPayload,
)
from src.modules.knowledge.infrastructure.adapters.parent_graph_checkpoint_storage import (
    ParentGraphCheckpointStorage,
)


class GraphJobWorker:
    """
    Worker autônomo para extração distribuída de subgrafos ontológicos via Redis Streams.
    Consome de 'stream:jobs:graph', reaproveita checkpoints locais sem custo de LLM,
    emite heartbeats e na barreira final consolida e persiste nós/arestas no FalkorDB em lote.
    """

    def __init__(
        self,
        stream_queue: IStreamJobQueue,
        storage: IObjectStorage,
        checkpoint_storage: ParentGraphCheckpointStorage,
        barrier: AtomicJobBarrier,
        graph_extractor: IGraphExtractor,
        graph_store: IGraphStore,
        document_repo: IDocumentRepository,
        pool: asyncpg.Pool | None = None,
        event_bus: EventBus | None = None,
        default_ontology: OntologySchema | None = None,
        stream_name: str = "stream:jobs:graph",
        group_name: str = "graph_workers",
        consumer_name: str | None = None,
        on_completed_callback: (
            Callable[[ParentGraphJobPayload, ExtractedGraph], Awaitable[None]] | None
        ) = None,
    ) -> None:
        self._stream_queue = stream_queue
        self._storage = storage
        self._checkpoint_storage = checkpoint_storage
        self._barrier = barrier
        self._graph_extractor = graph_extractor
        self._graph_store = graph_store
        self._document_repo = document_repo
        self._pool = pool
        self._event_bus = event_bus
        self._default_ontology = default_ontology or OntologySchema(
            name="GenericOntology",
            description="Default schema",
            node_types=[],
            relationship_types=[],
        )
        self._stream_name = stream_name
        self._group_name = group_name
        self._consumer_name = consumer_name or f"graph-worker-{uuid4().hex[:8]}"
        self._on_completed = on_completed_callback
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def run_once(self, count: int = 10, block_ms: int = 500) -> int:
        """Consome e processa tarefas de extração de subgrafo."""
        tasks = await self._stream_queue.consume_tasks(
            stream_name=self._stream_name,
            group_name=self._group_name,
            consumer_name=self._consumer_name,
            count=count,
            block_ms=block_ms,
        )
        if not tasks:
            tasks = await self._stream_queue.claim_stale_tasks(
                stream_name=self._stream_name,
                group_name=self._group_name,
                consumer_name=self._consumer_name,
                min_idle_time_ms=60000,
                count=count,
            )

        processed = 0
        for msg_id, task in tasks:
            success = await self.process_task(msg_id, task)
            if success:
                processed += 1
        return processed

    async def process_task(self, msg_id: str, task: JobTask) -> bool:
        """Executa a extração ontológica de um Parent Chunk com checkpoint durável."""
        try:
            payload = ParentGraphJobPayload.model_validate(task.payload)

            # 1. Verifica checkpoint durável em disco
            has_checkpoint = await self._checkpoint_storage.has_parent(
                kb_partition=payload.storage_partition,
                doc_id=payload.document_id,
                parent_id=payload.parent_id,
            )

            if not has_checkpoint:
                content = payload.content
                if not content and payload.content_storage_path:
                    raw_bytes = await self._storage.get_object(payload.content_storage_path)
                    content = raw_bytes.decode("utf-8")

                ontology = (
                    OntologySchema.model_validate(payload.ontology)
                    if payload.ontology
                    else self._default_ontology
                )

                extracted = await self._graph_extractor.extract_graph(
                    markdown_text=content,
                    ontology=ontology,
                    kb_id=payload.kb_id,
                )

                await self._checkpoint_storage.save_parent(
                    kb_partition=payload.storage_partition,
                    doc_id=payload.document_id,
                    parent_id=payload.parent_id,
                    graph=extracted,
                )

            # 2. Emite heartbeat
            await self._emit_heartbeat(payload.document_id)

            # 3. Barreira de junção atômica
            is_last = await self._barrier.increment_and_check(payload.document_id, step="graph")
            if is_last:
                await self._consolidate_and_index(payload)

            # 4. ACK no Redis Streams
            await self._stream_queue.ack_task(self._stream_name, self._group_name, msg_id)
            return True

        except Exception:
            return False

    async def _emit_heartbeat(self, doc_id: UUID) -> None:
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE attached_documents SET updated_at = NOW() WHERE id = $1;",
                doc_id,
            )

    async def _consolidate_and_index(self, payload: ParentGraphJobPayload) -> None:
        """Consolida todos os subgrafos, persiste no FalkorDB e atualiza o DocumentAggregate."""
        # Carrega os subgrafos de todos os parents
        all_nodes: dict[str, GraphNode] = {}
        all_edges: dict[tuple[str, str, str], GraphEdge] = {}

        parent_ids: list[str] = []
        chunks_path = f"{payload.storage_partition}/chunks/{payload.document_id}_chunks.json"
        if await self._storage.exists(chunks_path):
            try:
                raw_bytes = await self._storage.get_object(chunks_path)
                parsed = json.loads(raw_bytes.decode("utf-8"))
                parent_ids = [p["id"] for p in parsed.get("parents", []) if "id" in p]
            except Exception:
                parent_ids = []

        if not parent_ids:
            doc = await self._document_repo.get_by_id(payload.document_id)
            if doc is not None and doc.chunks_summary:
                parent_ids = [c["parent_id"] for c in doc.chunks_summary if "parent_id" in c]

        if not parent_ids:
            candidates: set[str] = {payload.parent_id}
            for idx in range(payload.total_parents):
                candidates.add(f"{payload.document_id}_parent_{idx}")
                candidates.add(f"{payload.document_id}-p{idx + 1}")
            parent_ids = list(candidates)

        for p_id in parent_ids:
            graph = await self._checkpoint_storage.get_parent(
                kb_partition=payload.storage_partition,
                doc_id=payload.document_id,
                parent_id=p_id,
            )
            if graph is None:
                continue

            for node in graph.nodes:
                key = f"{node.id}:{node.node_type}"
                all_nodes[key] = node

            for edge in graph.edges:
                edge_key = (edge.source_id, edge.target_id, edge.relationship_type)
                all_edges[edge_key] = edge

        merged_graph = ExtractedGraph(
            nodes=list(all_nodes.values()),
            edges=list(all_edges.values()),
        )

        # Grava no FalkorDB em lote (UNWIND)
        await self._graph_store.store_graph(payload.kb_id, merged_graph)

        # Salva o subgrafo unificado em storage
        subgraph_path = f"{payload.storage_partition}/graphs/{payload.document_id}.json"
        await self._storage.put_object(
            subgraph_path,
            merged_graph.model_dump_json().encode("utf-8"),
            "application/json",
        )

        # Atualiza o DocumentAggregate em stream autônomo O(1)
        doc = await self._document_repo.get_by_id(payload.document_id)
        if doc is not None:
            doc.mark_graph_extracted(
                node_count=len(merged_graph.nodes),
                edge_count=len(merged_graph.edges),
                subgraph_storage_path=subgraph_path,
                extracted_graph=None,
            )
            doc.mark_knowledge_indexed(
                indexed_nodes=len(merged_graph.nodes),
                indexed_edges=len(merged_graph.edges),
            )
            await self._document_repo.save(doc)

        if self._on_completed is not None:
            await self._on_completed(payload, merged_graph)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _worker_loop(self) -> None:
        while self._running:
            try:
                await self.run_once(count=10, block_ms=1000)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1.0)
