import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.application.logger import Logger
from src.kernel.domain.domain_event import DomainEvent
from src.kernel.infrastructure.atomic_job_barrier import AtomicJobBarrier
from src.modules.knowledge.domain.events.document_chunked_event import (
    DocumentChunkedEvent,
)
from src.modules.knowledge.domain.events.document_parsed_to_markdown_event import (
    DocumentParsedToMarkdownEvent,
)
from src.modules.knowledge.domain.events.document_progress_updated_event import (
    DocumentProgressUpdatedEvent,
)
from src.modules.knowledge.domain.events.document_stored_event import (
    DocumentStoredEvent,
)
from src.modules.knowledge.domain.events.graph_extracted_from_document_event import (
    GraphExtractedFromDocumentEvent,
)
from src.modules.knowledge.domain.interfaces.i_document_parser import (
    IDocumentParser,
)
from src.modules.knowledge.domain.interfaces.i_document_repository import (
    IDocumentRepository,
)
from src.modules.knowledge.domain.interfaces.i_embedding_service import (
    IEmbeddingService,
)
from src.modules.knowledge.domain.interfaces.i_graph_extractor import (
    IGraphExtractor,
)
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_markdown_chunker import (
    IMarkdownChunker,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import (
    IObjectStorage,
)
from src.modules.knowledge.domain.interfaces.i_stream_job_queue import (
    IStreamJobQueue,
)
from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.extracted_graph import (
    ExtractedGraph,
)
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.domain.value_objects.job_task import JobTask
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk
from src.modules.knowledge.domain.value_objects.parent_graph_job_payload import (
    ParentGraphJobPayload,
)
from src.modules.knowledge.domain.value_objects.structural_graph_document import (
    StructuralGraphDocument,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_embedding_service import (
    InMemoryEmbeddingService,
)
from src.modules.knowledge.infrastructure.adapters.page_checkpoint_storage import (
    PageCheckpointStorage,
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


class DocumentIngestionSagaCoordinator:
    """
    Saga Coreografada / Event-Driven Pipeline para Ingestão e Processamento GraphRAG.
    Escuta eventos do EventBus e transiciona o agregado através do pipeline com
    suporte a checkpoints atômicos, zero token waste e telemetria de progresso:
    Stored ➔ ParsedToMarkdown ➔ Chunked ➔ GraphExtracted ➔ KnowledgeIndexed.
    """

    def __init__(
        self,
        event_bus: EventBus,
        event_store: EventStore,
        kb_repository: IKnowledgeBaseRepository,
        storage: IObjectStorage,
        parser: IDocumentParser,
        extractor: IGraphExtractor,
        graph_store: IGraphStore,
        chunker: IMarkdownChunker | None = None,
        embedding_service: IEmbeddingService | None = None,
        logger: Logger | None = None,
        page_checkpoint_storage: PageCheckpointStorage | None = None,
        parent_graph_checkpoint_storage: (ParentGraphCheckpointStorage | None) = None,
        run_in_background: bool = False,
        document_repo: IDocumentRepository | None = None,
        stream_queue: IStreamJobQueue | None = None,
        barrier: AtomicJobBarrier | None = None,
    ) -> None:
        self._bus = event_bus
        self._store = event_store
        self._kb_repo = kb_repository
        self._document_repo = document_repo or PostgresDocumentRepository(event_store=self._store)
        self._stream_queue = stream_queue
        self._barrier = barrier
        self._storage = storage
        self._parser = parser
        self._extractor = extractor
        self._graph_store = graph_store
        self._chunker = chunker or StructureTolerantMarkdownChunker()
        self._embedding_service = embedding_service or InMemoryEmbeddingService()
        self._logger = logger
        self._page_checkpoint = page_checkpoint_storage
        self._graph_checkpoint = parent_graph_checkpoint_storage
        self._run_in_background = run_in_background
        self._background_tasks: set[asyncio.Task[Any]] = set()

        self._register_listeners()

    def _wrap_handler(
        self, handler: Callable[[DomainEvent], Coroutine[Any, Any, None]]
    ) -> Callable[[DomainEvent], Coroutine[Any, Any, None]]:
        if not self._run_in_background:
            return handler

        async def _bg_runner(event: DomainEvent) -> None:
            async def _safe_run() -> None:
                try:
                    await handler(event)
                except Exception as e:
                    import logging

                    logging.exception(f"Unhandled error in saga handler for {event}: {e}")

            task = asyncio.create_task(_safe_run())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return _bg_runner

    def _register_listeners(self) -> None:
        self._bus.subscribe(DocumentStoredEvent, self._wrap_handler(self.handle_document_stored))
        self._bus.subscribe(
            DocumentParsedToMarkdownEvent,
            self._wrap_handler(self.handle_document_parsed),
        )
        self._bus.subscribe(
            DocumentChunkedEvent,
            self._wrap_handler(self.handle_document_chunked),
        )
        self._bus.subscribe(
            GraphExtractedFromDocumentEvent,
            self._wrap_handler(self.handle_graph_extracted),
        )

    async def _record_failure_safely(
        self,
        document_id: UUID,
        step: str,
        error_message: str,
    ) -> None:
        try:
            doc = await self._document_repo.get_by_id(document_id)
            if doc is not None:
                doc.mark_processing_failed(step=step, error_message=error_message)
                await self._document_repo.save(doc)
            elif self._logger:
                self._logger.error(
                    f"DocumentAggregate {document_id} not found in step {step}: {error_message}"
                )
        except Exception as e:
            if self._logger:
                self._logger.error(
                    f"Falha ao registrar falha de processamento para doc {document_id}: {e}"
                )

    @staticmethod
    def _calculate_percentage(current: int, total: int) -> int:
        if total <= 0:
            return 0
        if current >= total:
            return 100
        return min(99, int((current / total) * 100))

    async def handle_document_stored(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentStoredEvent):
            return
        doc = await self._document_repo.get_by_id(event.document_id)
        if doc is None:
            if self._logger:
                self._logger.warning(
                    f"Doc {event.document_id} not found for handle_document_stored"
                )
            return

        kb_id = doc.kb_id or event.kb_id or event.aggregate_id
        kb = await self._kb_repo.get_by_id(kb_id) if kb_id else None
        storage_partition = kb.storage_partition if kb else str(kb_id)

        try:
            raw_bytes = await self._storage.get_object(event.storage_path)
            file_name = doc.file_name or "doc.txt"
            content_type = doc.content_type or "text/plain"
            enable_ocr = bool(doc.enable_ocr)
            ocr_instructions = doc.ocr_instructions

            async def _on_ocr_progress(cur: int, tot: int, msg: str) -> None:
                pct = self._calculate_percentage(cur, tot)
                await self._bus.publish(
                    [
                        DocumentProgressUpdatedEvent(
                            aggregate_id=event.aggregate_id,
                            document_id=event.document_id,
                            kb_id=kb_id,
                            step="OCR",
                            current=cur,
                            total=tot,
                            percentage=pct,
                            message=msg,
                        )
                    ]
                )

            ingested_at = doc.ingested_at

            markdown_text = await self._parser.parse_to_markdown(
                raw_bytes=raw_bytes,
                file_name=file_name,
                content_type=content_type,
                enable_ocr=enable_ocr,
                ocr_instructions=ocr_instructions,
                doc_id=event.document_id,
                kb_partition=storage_partition,
                progress_callback=_on_ocr_progress,
                ingested_at=ingested_at,
            )
            md_path = f"{storage_partition}/markdown/{event.document_id}.md"
            await self._storage.put_object(md_path, markdown_text.encode("utf-8"), "text/markdown")

            doc.mark_parsed(
                markdown_storage_path=md_path,
                markdown_preview=markdown_text[:200],
            )
            await self._document_repo.save(doc)
        except Exception as e:
            await self._record_failure_safely(
                document_id=event.document_id,
                step="PARSE_MARKDOWN",
                error_message=str(e),
            )

    async def handle_document_parsed(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentParsedToMarkdownEvent):
            return
        doc = await self._document_repo.get_by_id(event.document_id)
        if doc is None:
            if self._logger:
                self._logger.warning(
                    f"Doc {event.document_id} not found for handle_document_parsed"
                )
            return

        kb_id = doc.kb_id or event.kb_id or event.aggregate_id
        kb = await self._kb_repo.get_by_id(kb_id) if kb_id else None
        storage_partition = kb.storage_partition if kb else str(kb_id)

        try:
            await self._bus.publish(
                [
                    DocumentProgressUpdatedEvent(
                        aggregate_id=event.aggregate_id,
                        document_id=event.document_id,
                        kb_id=kb_id,
                        step="CHUNKING",
                        current=0,
                        total=1,
                        percentage=0,
                        message="Fatiando documento em Chunks Hierárquicos (Pai/Filho)...",
                    )
                ]
            )
            md_bytes = await self._storage.get_object(event.markdown_storage_path)
            md_text = md_bytes.decode("utf-8")
            file_name = doc.file_name or "document.md"
            source_type = doc.source_type
            ingested_at = doc.ingested_at

            chunk_collection = await self._chunker.chunk(
                document_id=event.document_id,
                document_name=file_name,
                markdown_text=md_text,
                source_type=source_type,
                ingested_at=ingested_at,
            )

            chunks_path = f"{storage_partition}/chunks/{event.document_id}_chunks.json"
            chunks_data = {
                "parents": [p.model_dump() for p in chunk_collection.parents],
                "children": [c.model_dump() for c in chunk_collection.children],
            }
            await self._storage.put_object(
                chunks_path,
                json.dumps(chunks_data, ensure_ascii=False).encode("utf-8"),
                "application/json",
            )

            summary = [
                {
                    "parent_id": p.id,
                    "header_path": p.header_path,
                    "token_count": p.token_count,
                }
                for p in chunk_collection.parents
            ]

            doc.mark_chunked(
                total_parents=len(chunk_collection.parents),
                total_children=len(chunk_collection.children),
                chunks_summary=summary,
            )
            await self._document_repo.save(doc)
        except Exception as e:
            await self._record_failure_safely(
                document_id=event.document_id,
                step="MARKDOWN_CHUNKING",
                error_message=str(e),
            )

    async def handle_document_chunked(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentChunkedEvent):
            return
        doc = await self._document_repo.get_by_id(event.document_id)
        if doc is None:
            if self._logger:
                self._logger.warning(
                    f"Doc {event.document_id} not found for handle_document_chunked"
                )
            return

        kb_id = doc.kb_id or event.kb_id or event.aggregate_id
        if not kb_id:
            return
        kb = await self._kb_repo.get_by_id(kb_id)
        if kb is None:
            raise ValueError(f"KnowledgeBase {kb_id} not found")

        try:
            if not kb.ontology:
                raise ValueError("Ontology is missing in Knowledge Base")

            storage_partition = kb.storage_partition
            md_path = (
                doc.markdown_storage_path or f"{storage_partition}/markdown/{event.document_id}.md"
            )
            file_name = doc.file_name or "document.md"

            chunks_path = f"{storage_partition}/chunks/{event.document_id}_chunks.json"
            if await self._storage.exists(chunks_path):
                raw_chunks = await self._storage.get_object(chunks_path)
                parsed_json = json.loads(raw_chunks.decode("utf-8"))
                parents = [ParentChunk.model_validate(p) for p in parsed_json.get("parents", [])]
                children = [ChildChunk.model_validate(c) for c in parsed_json.get("children", [])]
            else:
                md_bytes = await self._storage.get_object(md_path)
                md_text = md_bytes.decode("utf-8")
                chunk_collection = await self._chunker.chunk(
                    document_id=event.document_id,
                    document_name=file_name,
                    markdown_text=md_text,
                )
                parents = chunk_collection.parents
                children = chunk_collection.children

            embedded_children: list[ChildChunk] = []
            if children:
                await self._bus.publish(
                    [
                        DocumentProgressUpdatedEvent(
                            aggregate_id=event.aggregate_id,
                            document_id=event.document_id,
                            kb_id=kb_id,
                            step="EMBEDDINGS",
                            current=0,
                            total=len(children),
                            percentage=0,
                            message=(
                                f"Gerando representações vetoriais "
                                f"(0/{len(children)} Chunks Filhos)..."
                            ),
                        )
                    ]
                )
                child_texts = [c.content for c in children]
                child_titles = [f"{file_name} > {c.header_path}" for c in children]

                batch_size = 50
                all_embeddings: list[list[float] | None] = []
                for i in range(0, len(child_texts), batch_size):
                    b_texts = child_texts[i : i + batch_size]
                    b_titles = child_titles[i : i + batch_size]
                    b_embs = await self._embedding_service.embed_texts(b_texts, b_titles)
                    all_embeddings.extend(b_embs)
                    cur_emb = min(len(all_embeddings), len(children))
                    pct_emb = self._calculate_percentage(cur_emb, len(children))
                    await self._bus.publish(
                        [
                            DocumentProgressUpdatedEvent(
                                aggregate_id=event.aggregate_id,
                                document_id=event.document_id,
                                kb_id=kb_id,
                                step="EMBEDDINGS",
                                current=cur_emb,
                                total=len(children),
                                percentage=pct_emb,
                                message=(
                                    f"Gerando representações vetoriais "
                                    f"({cur_emb}/{len(children)} Chunks Filhos)..."
                                ),
                            )
                        ]
                    )

                for idx, child in enumerate(children):
                    emb = all_embeddings[idx] if idx < len(all_embeddings) else None
                    embedded_children.append(
                        ChildChunk(
                            id=child.id,
                            parent_chunk_id=child.parent_chunk_id,
                            chunk_index=child.chunk_index,
                            header_path=child.header_path,
                            content=child.content,
                            embedding=emb,
                            metadata=child.metadata,
                        )
                    )

            structural_doc = StructuralGraphDocument(
                document_id=event.document_id,
                document_name=file_name,
                parents=parents,
                children=embedded_children,
            )
            await self._graph_store.ensure_vector_index(kb.id)
            await self._graph_store.store_structural_document(kb.id, structural_doc)

            assert kb.ontology is not None
            current_ontology = kb.ontology
            valid_parents = [p for p in parents if p.content.strip()]
            total_parents = len(valid_parents)

            if self._stream_queue is not None and self._barrier is not None:
                await self._barrier.init_barrier(
                    event.document_id, total_chunks=total_parents, step="graph"
                )
                doc_meta = dict(doc.metadata or getattr(event, "metadata", None) or {})
                for idx, parent in enumerate(valid_parents):
                    payload = ParentGraphJobPayload(
                        kb_id=kb.id,
                        document_id=event.document_id,
                        parent_id=parent.id,
                        parent_index=idx,
                        total_parents=total_parents,
                        header_path=parent.header_path,
                        storage_partition=kb.storage_partition,
                        content=parent.content,
                        ontology=current_ontology.model_dump() if current_ontology else {},
                        metadata=doc_meta,
                    )
                    task = JobTask(
                        id=f"{event.document_id}_{parent.id}",
                        queue_name="stream:jobs:graph",
                        payload=payload.model_dump(mode="json"),
                    )
                    await self._stream_queue.publish_task("stream:jobs:graph", task)

                await self._bus.publish(
                    [
                        DocumentProgressUpdatedEvent(
                            aggregate_id=event.aggregate_id,
                            document_id=event.document_id,
                            kb_id=kb_id,
                            step="GRAPH_EXTRACTION",
                            current=0,
                            total=total_parents,
                            percentage=0,
                            message=(
                                "Tarefas de extração ontológica despachadas para Redis Streams "
                                f"({total_parents} Chunks)..."
                            ),
                        )
                    ]
                )
                return

            completed_parents = 0
            parent_lock = asyncio.Lock()

            await self._bus.publish(
                [
                    DocumentProgressUpdatedEvent(
                        aggregate_id=event.aggregate_id,
                        document_id=event.document_id,
                        kb_id=kb_id,
                        step="GRAPH_EXTRACTION",
                        current=0,
                        total=total_parents,
                        percentage=0,
                        message=(
                            f"Iniciando extração ontológica com LLM (0/{total_parents} Chunks)..."
                        ),
                    )
                ]
            )

            async def _extract_single_parent(
                parent: ParentChunk, idx: int
            ) -> tuple[str, ExtractedGraph]:
                nonlocal completed_parents
                if self._graph_checkpoint:
                    if await self._graph_checkpoint.has_parent(
                        kb.storage_partition, event.document_id, parent.id
                    ):
                        cached = await self._graph_checkpoint.get_parent(
                            kb.storage_partition, event.document_id, parent.id
                        )
                        if cached is not None:
                            async with parent_lock:
                                completed_parents += 1
                                cur_parent = completed_parents

                            pct = self._calculate_percentage(cur_parent, total_parents)
                            await self._bus.publish(
                                [
                                    DocumentProgressUpdatedEvent(
                                        aggregate_id=event.aggregate_id,
                                        document_id=event.document_id,
                                        kb_id=kb_id,
                                        step="GRAPH_EXTRACTION",
                                        current=cur_parent,
                                        total=total_parents,
                                        percentage=pct,
                                        message=(
                                            f"Chunk {cur_parent} de {total_parents}"
                                            " (Reutilizado do Cache)"
                                        ),
                                    )
                                ]
                            )
                            return parent.id, cached

                parent_graph = await self._extractor.extract_graph(
                    markdown_text=parent.content,
                    ontology=current_ontology,
                    kb_id=kb.id,
                )

                if self._graph_checkpoint:
                    await self._graph_checkpoint.save_parent(
                        kb.storage_partition,
                        event.document_id,
                        parent.id,
                        parent_graph,
                    )

                async with parent_lock:
                    completed_parents += 1
                    cur_parent = completed_parents

                pct = self._calculate_percentage(cur_parent, total_parents)
                await self._bus.publish(
                    [
                        DocumentProgressUpdatedEvent(
                            aggregate_id=event.aggregate_id,
                            document_id=event.document_id,
                            kb_id=kb_id,
                            step="GRAPH_EXTRACTION",
                            current=cur_parent,
                            total=total_parents,
                            percentage=pct,
                            message=(f"Chunk {cur_parent} de {total_parents} extraído via LLM"),
                        )
                    ]
                )
                return parent.id, parent_graph

            chunk_semaphore = asyncio.Semaphore(15)

            async def _bounded_extract(parent: ParentChunk, idx: int) -> tuple[str, ExtractedGraph]:
                async with chunk_semaphore:
                    return await _extract_single_parent(parent, idx)

            extraction_results = await asyncio.gather(
                *(_bounded_extract(p, idx) for idx, p in enumerate(valid_parents))
            )

            all_nodes: dict[str, GraphNode] = {}
            all_edges: list[GraphEdge] = []

            for parent_id, parent_graph in extraction_results:
                if parent_graph.nodes or parent_graph.edges:
                    await self._graph_store.store_parent_mentions(kb.id, parent_id, parent_graph)
                    for n in parent_graph.nodes:
                        all_nodes[n.id] = n
                    all_edges.extend(parent_graph.edges)

            combined_graph = ExtractedGraph(
                nodes=list(all_nodes.values()),
                edges=all_edges,
            )
            doc.mark_graph_extracted(
                node_count=len(combined_graph.nodes),
                edge_count=len(combined_graph.edges),
                subgraph_storage_path=f"{kb.storage_partition}/graphs/{event.document_id}.json",
                extracted_graph=combined_graph,
            )
            await self._document_repo.save(doc)
        except Exception as e:
            await self._record_failure_safely(
                document_id=event.document_id,
                step="GRAPH_EXTRACTION",
                error_message=str(e),
            )

    async def handle_graph_extracted(self, event: DomainEvent) -> None:
        if not isinstance(event, GraphExtractedFromDocumentEvent):
            return
        doc = await self._document_repo.get_by_id(event.document_id)
        if doc is None:
            if self._logger:
                self._logger.warning(
                    f"Doc {event.document_id} not found for handle_graph_extracted"
                )
            return

        kb_id = doc.kb_id or event.kb_id or event.aggregate_id
        if not kb_id:
            return

        try:
            await self._bus.publish(
                [
                    DocumentProgressUpdatedEvent(
                        aggregate_id=event.aggregate_id,
                        document_id=event.document_id,
                        kb_id=kb_id,
                        step="INDEXING",
                        current=0,
                        total=1,
                        percentage=0,
                        message="Persistindo subgrafo e índices no FalkorDB...",
                    )
                ]
            )
            extracted_graph = event.extracted_graph
            if extracted_graph is None:
                if event.subgraph_storage_path and await self._storage.exists(
                    event.subgraph_storage_path
                ):
                    raw_bytes = await self._storage.get_object(event.subgraph_storage_path)
                    extracted_graph = ExtractedGraph.model_validate_json(raw_bytes.decode("utf-8"))
                else:
                    extracted_graph = ExtractedGraph(nodes=[], edges=[])

            indexed_nodes, indexed_edges = await self._graph_store.store_graph(
                kb_id, extracted_graph
            )

            doc.mark_knowledge_indexed(
                indexed_nodes=indexed_nodes,
                indexed_edges=indexed_edges,
            )
            await self._document_repo.save(doc)

            await self._bus.publish(
                [
                    DocumentProgressUpdatedEvent(
                        aggregate_id=event.aggregate_id,
                        document_id=event.document_id,
                        kb_id=kb_id,
                        step="INDEXED",
                        current=1,
                        total=1,
                        percentage=100,
                        message="Processamento e indexação concluídos com sucesso",
                    )
                ]
            )
        except Exception as e:
            await self._record_failure_safely(
                document_id=event.document_id,
                step="INDEXING",
                error_message=str(e),
            )
