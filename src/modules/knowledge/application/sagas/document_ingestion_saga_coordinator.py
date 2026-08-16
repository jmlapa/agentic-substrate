from uuid import UUID

from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.application.logger import Logger
from src.kernel.domain.domain_event import DomainEvent
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
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
from src.modules.knowledge.domain.interfaces.i_graph_extractor import (
    IGraphExtractor,
)
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.domain.interfaces.i_vector_store import IVectorStore


class DocumentIngestionSagaCoordinator:
    """
    Saga Coreografada / Event-Driven Pipeline para Ingestão e Processamento GraphRAG.
    Escuta eventos do EventBus e executa os passos transicionando o estado do agregado.
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
        vector_store: IVectorStore,
        logger: Logger | None = None,
    ) -> None:
        self._bus = event_bus
        self._store = event_store
        self._kb_repo = kb_repository
        self._storage = storage
        self._parser = parser
        self._extractor = extractor
        self._graph_store = graph_store
        self._vector_store = vector_store
        self._logger = logger

        self._register_listeners()

    def _register_listeners(self) -> None:
        self._bus.subscribe(DocumentStoredEvent, self.handle_document_stored)
        self._bus.subscribe(DocumentParsedToMarkdownEvent, self.handle_document_parsed)
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
            if not kb.ontology:
                raise ValueError("Ontology is missing in Knowledge Base")

            md_bytes = await self._storage.get_object(event.markdown_storage_path)
            md_text = md_bytes.decode("utf-8")

            extracted_graph = await self._extractor.extract_graph(md_text, kb.ontology)
            kb.mark_graph_extracted(event.document_id, extracted_graph)
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
            await self._vector_store.store_node_embeddings(kb.id, event.extracted_graph)

            kb.mark_knowledge_indexed(
                document_id=event.document_id,
                indexed_nodes=indexed_nodes,
                indexed_edges=indexed_edges,
            )
            await self._save_aggregate(kb)
        except Exception as e:
            kb.mark_processing_failed(event.document_id, step="INDEXING", error_message=str(e))
            await self._save_aggregate(kb)
