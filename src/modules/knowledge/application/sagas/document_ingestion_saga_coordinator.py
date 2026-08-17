import asyncio
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
from src.modules.knowledge.domain.events.document_stored_event import DocumentStoredEvent
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
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
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
from src.modules.knowledge.infrastructure.chunking.structure_tolerant_markdown_chunker import (
    StructureTolerantMarkdownChunker,
)


class DocumentIngestionSagaCoordinator:
    """
    Saga Coreografada / Event-Driven Pipeline para Ingestão e Processamento GraphRAG.
    Escuta eventos do EventBus e transiciona o agregado através do pipeline:
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

        self._register_listeners()

    def _register_listeners(self) -> None:
        self._bus.subscribe(DocumentStoredEvent, self.handle_document_stored)
        self._bus.subscribe(DocumentParsedToMarkdownEvent, self.handle_document_parsed)
        self._bus.subscribe(DocumentChunkedEvent, self.handle_document_chunked)
        self._bus.subscribe(GraphExtractedFromDocumentEvent, self.handle_graph_extracted)

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

    async def handle_document_stored(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentStoredEvent):
            return
        kb = await self._load_aggregate(event.aggregate_id)
        try:
            raw_bytes = await self._storage.get_object(event.storage_path)
            doc_info = kb.documents.get(event.document_id, {})
            file_name = doc_info.get("file_name", "doc.txt")
            content_type = doc_info.get("content_type", "text/plain")

            markdown_text = await self._parser.parse_to_markdown(raw_bytes, file_name, content_type)
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
            md_bytes = await self._storage.get_object(event.markdown_storage_path)
            md_text = md_bytes.decode("utf-8")
            doc_info = kb.documents.get(event.document_id, {})
            file_name = doc_info.get("file_name", "document.md")

            chunk_collection = await self._chunker.chunk(
                document_id=event.document_id,
                document_name=file_name,
                markdown_text=md_text,
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
                event.document_id, step="MARKDOWN_CHUNKING", error_message=str(e)
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
                "markdown_path", f"{kb.storage_partition}/markdown/{event.document_id}.md"
            )
            file_name = doc_info.get("file_name", "document.md")

            md_bytes = await self._storage.get_object(md_path)
            md_text = md_bytes.decode("utf-8")

            # 1. Obter chunks e gerar embeddings para os Child Chunks
            chunk_collection = await self._chunker.chunk(
                document_id=event.document_id,
                document_name=file_name,
                markdown_text=md_text,
            )

            embedded_children: list[ChildChunk] = []
            if chunk_collection.children:
                child_texts = [c.content for c in chunk_collection.children]
                child_titles = [f"{file_name} > {c.header_path}" for c in chunk_collection.children]
                embeddings = await self._embedding_service.embed_texts(child_texts, child_titles)

                for idx, child in enumerate(chunk_collection.children):
                    emb = embeddings[idx] if idx < len(embeddings) else None
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
                parents=chunk_collection.parents,
                children=embedded_children,
            )
            await self._graph_store.ensure_vector_index(kb.id)
            await self._graph_store.store_structural_document(kb.id, structural_doc)

            # 3. Extrair grafo ontológico concorrentemente por Parent Chunk
            assert kb.ontology is not None
            current_ontology = kb.ontology
            valid_parents = [p for p in chunk_collection.parents if p.content.strip()]

            async def _extract_single_parent(
                parent: ParentChunk,
            ) -> tuple[str, ExtractedGraph]:
                parent_graph = await self._extractor.extract_graph(
                    markdown_text=parent.content,
                    ontology=current_ontology,
                    kb_id=kb.id,
                )
                return parent.id, parent_graph

            extraction_results = await asyncio.gather(
                *(_extract_single_parent(p) for p in valid_parents)
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
            indexed_nodes, indexed_edges = await self._graph_store.store_graph(
                kb.id, event.extracted_graph
            )

            kb.mark_knowledge_indexed(
                document_id=event.document_id,
                indexed_nodes=indexed_nodes,
                indexed_edges=indexed_edges,
            )
            await self._save_aggregate(kb)
        except Exception as e:
            kb.mark_processing_failed(event.document_id, step="INDEXING", error_message=str(e))
            await self._save_aggregate(kb)
