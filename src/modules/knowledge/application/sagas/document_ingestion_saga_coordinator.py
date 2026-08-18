import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.application.logger import Logger
from src.kernel.domain.domain_event import DomainEvent
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
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
from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.extracted_graph import (
    ExtractedGraph,
)
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk
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
    ) -> None:
        self._bus = event_bus
        self._store = event_store
        self._kb_repo = kb_repository
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

    async def _load_aggregate(self, kb_id: UUID) -> KnowledgeBaseAggregate:
        events = await self._store.get_events(kb_id)
        kb = KnowledgeBaseAggregate(id=kb_id)
        kb.load_from_history(events)
        return kb

    async def _save_aggregate(self, kb: KnowledgeBaseAggregate) -> None:
        expected_version = kb.version - len(kb.uncommitted_events)
        events_to_publish = list(kb.uncommitted_events)
        kb.mark_events_as_committed()
        await self._kb_repo.save(kb)
        await self._store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=events_to_publish,
            expected_version=expected_version,
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
        kb = await self._load_aggregate(event.aggregate_id)
        try:
            raw_bytes = await self._storage.get_object(event.storage_path)
            doc_info = kb.documents.get(event.document_id, {})
            file_name = doc_info.get("file_name", "doc.txt")
            content_type = doc_info.get("content_type", "text/plain")
            enable_ocr = bool(doc_info.get("enable_ocr", False))
            ocr_instructions = doc_info.get("ocr_instructions")

            async def _on_ocr_progress(cur: int, tot: int, msg: str) -> None:
                pct = self._calculate_percentage(cur, tot)
                await self._bus.publish(
                    [
                        DocumentProgressUpdatedEvent(
                            aggregate_id=event.aggregate_id,
                            document_id=event.document_id,
                            step="OCR",
                            current=cur,
                            total=tot,
                            percentage=pct,
                            message=msg,
                        )
                    ]
                )

            markdown_text = await self._parser.parse_to_markdown(
                raw_bytes=raw_bytes,
                file_name=file_name,
                content_type=content_type,
                enable_ocr=enable_ocr,
                ocr_instructions=ocr_instructions,
                doc_id=event.document_id,
                kb_partition=kb.storage_partition,
                progress_callback=_on_ocr_progress,
            )
            md_path = f"{kb.storage_partition}/markdown/{event.document_id}.md"
            await self._storage.put_object(md_path, markdown_text.encode("utf-8"), "text/markdown")

            kb.mark_document_parsed(
                document_id=event.document_id,
                markdown_storage_path=md_path,
                markdown_preview=markdown_text[:200],
            )
            await self._save_aggregate(kb)
        except Exception as e:
            kb.mark_processing_failed(
                event.document_id, step="PARSE_MARKDOWN", error_message=str(e)
            )
            await self._save_aggregate(kb)

    async def handle_document_parsed(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentParsedToMarkdownEvent):
            return
        kb = await self._load_aggregate(event.aggregate_id)
        try:
            await self._bus.publish(
                [
                    DocumentProgressUpdatedEvent(
                        aggregate_id=event.aggregate_id,
                        document_id=event.document_id,
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
            doc_info = kb.documents.get(event.document_id, {})
            file_name = doc_info.get("file_name", "document.md")

            chunk_collection = await self._chunker.chunk(
                document_id=event.document_id,
                document_name=file_name,
                markdown_text=md_text,
            )

            # Persiste chunks serializados para evitar re-chunking redundante
            chunks_path = f"{kb.storage_partition}/chunks/{event.document_id}_chunks.json"
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

            kb.mark_document_chunked(
                document_id=event.document_id,
                total_parents=len(chunk_collection.parents),
                total_children=len(chunk_collection.children),
                chunks_summary=summary,
            )
            await self._save_aggregate(kb)
        except Exception as e:
            kb.mark_processing_failed(
                event.document_id,
                step="MARKDOWN_CHUNKING",
                error_message=str(e),
            )
            await self._save_aggregate(kb)

    async def handle_document_chunked(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentChunkedEvent):
            return
        kb = await self._load_aggregate(event.aggregate_id)
        try:
            if not kb.ontology:
                raise ValueError("Ontology is missing in Knowledge Base")

            doc_info = kb.documents.get(event.document_id, {})
            md_path = doc_info.get(
                "markdown_path",
                f"{kb.storage_partition}/markdown/{event.document_id}.md",
            )
            file_name = doc_info.get("file_name", "document.md")

            # Recupera chunks do cache se disponível para evitar re-chunking
            chunks_path = f"{kb.storage_partition}/chunks/{event.document_id}_chunks.json"
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

            # 1. Geração de Embeddings em Micro-batches de 50 chunks
            embedded_children: list[ChildChunk] = []
            if children:
                await self._bus.publish(
                    [
                        DocumentProgressUpdatedEvent(
                            aggregate_id=event.aggregate_id,
                            document_id=event.document_id,
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

            # 2. Ingestão Estrutural no FalkorDB Graph Store (Document -> Parent -> Child)
            structural_doc = StructuralGraphDocument(
                document_id=event.document_id,
                document_name=file_name,
                parents=parents,
                children=embedded_children,
            )
            await self._graph_store.ensure_vector_index(kb.id)
            await self._graph_store.store_structural_document(kb.id, structural_doc)

            # 3. Extrair grafo ontológico concorrentemente por Parent Chunk com Checkpoints
            assert kb.ontology is not None
            current_ontology = kb.ontology
            valid_parents = [p for p in parents if p.content.strip()]
            total_parents = len(valid_parents)
            completed_parents = 0
            parent_lock = asyncio.Lock()

            await self._bus.publish(
                [
                    DocumentProgressUpdatedEvent(
                        aggregate_id=event.aggregate_id,
                        document_id=event.document_id,
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
                # Checagem de Checkpoint no Disco (Zero Token Waste)
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
                            step="GRAPH_EXTRACTION",
                            current=cur_parent,
                            total=total_parents,
                            percentage=pct,
                            message=(f"Chunk {cur_parent} de {total_parents} extraído via LLM"),
                        )
                    ]
                )
                return parent.id, parent_graph

            extraction_results = await asyncio.gather(
                *(_extract_single_parent(p, idx) for idx, p in enumerate(valid_parents))
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
            kb.mark_graph_extracted(event.document_id, combined_graph)
            await self._save_aggregate(kb)
        except Exception as e:
            kb.mark_processing_failed(
                event.document_id, step="GRAPH_EXTRACTION", error_message=str(e)
            )
            await self._save_aggregate(kb)

    async def handle_graph_extracted(self, event: DomainEvent) -> None:
        if not isinstance(event, GraphExtractedFromDocumentEvent):
            return
        kb = await self._load_aggregate(event.aggregate_id)
        try:
            await self._bus.publish(
                [
                    DocumentProgressUpdatedEvent(
                        aggregate_id=event.aggregate_id,
                        document_id=event.document_id,
                        step="INDEXING",
                        current=0,
                        total=1,
                        percentage=0,
                        message="Persistindo subgrafo e índices no FalkorDB...",
                    )
                ]
            )
            indexed_nodes, indexed_edges = await self._graph_store.store_graph(
                kb.id, event.extracted_graph
            )

            kb.mark_knowledge_indexed(
                document_id=event.document_id,
                indexed_nodes=indexed_nodes,
                indexed_edges=indexed_edges,
            )
            await self._save_aggregate(kb)

            await self._bus.publish(
                [
                    DocumentProgressUpdatedEvent(
                        aggregate_id=event.aggregate_id,
                        document_id=event.document_id,
                        step="INDEXED",
                        current=1,
                        total=1,
                        percentage=100,
                        message="Processamento e indexação concluídos com sucesso",
                    )
                ]
            )
        except Exception as e:
            kb.mark_processing_failed(event.document_id, step="INDEXING", error_message=str(e))
            await self._save_aggregate(kb)
