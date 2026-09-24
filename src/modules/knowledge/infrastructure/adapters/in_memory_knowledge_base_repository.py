from uuid import UUID

from src.kernel.application.event_bus import EventBus
from src.kernel.domain.domain_event import DomainEvent
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.events.document_attached_event import (
    DocumentAttachedEvent,
)
from src.modules.knowledge.domain.events.document_chunked_event import (
    DocumentChunkedEvent,
)
from src.modules.knowledge.domain.events.document_deleted_event import (
    DocumentDeletedEvent,
)
from src.modules.knowledge.domain.events.document_knowledge_indexed_event import (
    DocumentKnowledgeIndexedEvent,
)
from src.modules.knowledge.domain.events.document_parsed_to_markdown_event import (
    DocumentParsedToMarkdownEvent,
)
from src.modules.knowledge.domain.events.document_processing_failed_event import (
    DocumentProcessingFailedEvent,
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
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus


class InMemoryKnowledgeBaseRepository(IKnowledgeBaseRepository):
    """
    Repositório em memória para KnowledgeBaseAggregate com suporte a projeção
    CQRS reativa via EventBus para testes unitários e de integração.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._kbs: dict[UUID, KnowledgeBaseAggregate] = {}
        if event_bus is not None:
            self._register_listeners(event_bus)

    def _register_listeners(self, bus: EventBus) -> None:
        bus.subscribe(DocumentAttachedEvent, self._handle_attached)
        bus.subscribe(DocumentStoredEvent, self._handle_stored)
        bus.subscribe(DocumentParsedToMarkdownEvent, self._handle_parsed)
        bus.subscribe(DocumentChunkedEvent, self._handle_chunked)
        bus.subscribe(GraphExtractedFromDocumentEvent, self._handle_graph_extracted)
        bus.subscribe(DocumentKnowledgeIndexedEvent, self._handle_indexed)
        bus.subscribe(DocumentProcessingFailedEvent, self._handle_failed)
        bus.subscribe(DocumentProgressUpdatedEvent, self._handle_progress)
        bus.subscribe(DocumentDeletedEvent, self._handle_deleted)

    async def _handle_attached(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentAttachedEvent):
            return
        kb_id = event.kb_id or event.aggregate_id
        kb = self._kbs.get(kb_id)
        if kb is not None:
            kb.documents[event.document_id] = {
                "id": event.document_id,
                "file_name": event.file_name,
                "content_type": event.content_type,
                "storage_path": event.storage_path,
                "source_type": event.source_type,
                "status": DocumentStatus.PENDING_UPLOAD,
                "enable_ocr": event.enable_ocr,
                "ocr_instructions": event.ocr_instructions,
                "ingested_at": event.ingested_at,
                "total_parents": 0,
                "total_children": 0,
                "indexed_nodes_count": 0,
                "indexed_edges_count": 0,
                "progress_step": None,
                "progress_current": 0,
                "progress_total": 0,
                "progress_percentage": 0,
                "progress_message": None,
                "error": None,
            }

    async def _handle_stored(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentStoredEvent):
            return
        for kb in self._kbs.values():
            if event.document_id in kb.documents:
                doc = kb.documents[event.document_id]
                doc["status"] = DocumentStatus.UPLOADED
                doc["storage_path"] = event.storage_path
                doc["byte_size"] = event.byte_size
                doc["error"] = None

    async def _handle_parsed(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentParsedToMarkdownEvent):
            return
        for kb in self._kbs.values():
            if event.document_id in kb.documents:
                doc = kb.documents[event.document_id]
                doc["status"] = DocumentStatus.PARSED
                doc["markdown_path"] = event.markdown_storage_path
                doc["markdown_preview"] = event.markdown_preview

    async def _handle_chunked(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentChunkedEvent):
            return
        for kb in self._kbs.values():
            if event.document_id in kb.documents:
                doc = kb.documents[event.document_id]
                doc["status"] = DocumentStatus.CHUNKED
                doc["total_parents"] = event.total_parents
                doc["total_children"] = event.total_children

    async def _handle_graph_extracted(self, event: DomainEvent) -> None:
        if not isinstance(event, GraphExtractedFromDocumentEvent):
            return
        for kb in self._kbs.values():
            if event.document_id in kb.documents:
                doc = kb.documents[event.document_id]
                doc["status"] = DocumentStatus.GRAPH_EXTRACTED
                doc["indexed_nodes_count"] = event.node_count
                doc["indexed_edges_count"] = event.edge_count

    async def _handle_indexed(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentKnowledgeIndexedEvent):
            return
        for kb in self._kbs.values():
            if event.document_id in kb.documents:
                doc = kb.documents[event.document_id]
                doc["status"] = DocumentStatus.INDEXED
                doc["indexed_nodes_count"] = event.indexed_nodes_count
                doc["indexed_edges_count"] = event.indexed_edges_count
                doc["progress_step"] = "INDEXED"
                doc["progress_percentage"] = 100
                doc["progress_message"] = "Processamento e indexação concluídos com sucesso"

    async def _handle_failed(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentProcessingFailedEvent):
            return
        for kb in self._kbs.values():
            if event.document_id in kb.documents:
                doc = kb.documents[event.document_id]
                doc["status"] = DocumentStatus.FAILED
                doc["error"] = {
                    "step": event.step,
                    "message": event.error_message,
                    "error_message": event.error_message,
                }

    async def _handle_progress(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentProgressUpdatedEvent):
            return
        for kb in self._kbs.values():
            if event.document_id in kb.documents:
                doc = kb.documents[event.document_id]
                doc["progress_step"] = event.step
                doc["progress_current"] = event.current
                doc["progress_total"] = event.total
                doc["progress_percentage"] = event.percentage
                doc["progress_message"] = event.message

    async def _handle_deleted(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentDeletedEvent):
            return
        for kb in self._kbs.values():
            kb.documents.pop(event.document_id, None)

    async def save(self, aggregate: KnowledgeBaseAggregate) -> None:
        existing = self._kbs.get(aggregate.id)
        if existing is not None and not aggregate.documents and existing.documents:
            # Preserva a projeção de documentos existente em memória
            aggregate.documents = dict(existing.documents)
        self._kbs[aggregate.id] = aggregate

    async def get_by_id(self, id: UUID) -> KnowledgeBaseAggregate | None:
        return self._kbs.get(id)

    async def list_all(self) -> list[KnowledgeBaseAggregate]:
        return list(self._kbs.values())

    async def delete_by_id(self, id: UUID) -> None:
        self._kbs.pop(id, None)

    async def delete_document(self, kb_id: UUID, document_id: UUID) -> None:
        if kb_id in self._kbs:
            self._kbs[kb_id].documents.pop(document_id, None)
