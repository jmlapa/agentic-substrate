import time
from typing import Any
from uuid import UUID, uuid4

from src.kernel.domain.aggregate_root import AggregateRoot
from src.modules.knowledge.domain.events.document_attached_event import DocumentAttachedEvent
from src.modules.knowledge.domain.events.document_chunked_event import DocumentChunkedEvent
from src.modules.knowledge.domain.events.document_deleted_event import DocumentDeletedEvent
from src.modules.knowledge.domain.events.document_knowledge_indexed_event import (
    DocumentKnowledgeIndexedEvent,
)
from src.modules.knowledge.domain.events.document_parsed_to_markdown_event import (
    DocumentParsedToMarkdownEvent,
)
from src.modules.knowledge.domain.events.document_processing_failed_event import (
    DocumentProcessingFailedEvent,
)
from src.modules.knowledge.domain.events.document_stored_event import DocumentStoredEvent
from src.modules.knowledge.domain.events.graph_extracted_from_document_event import (
    GraphExtractedFromDocumentEvent,
)
from src.modules.knowledge.domain.value_objects.document_source_type import DocumentSourceType
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph


class DocumentAggregate(AggregateRoot):
    """
    Aggregate Root autônomo para o ciclo de vida individual de um documento.
    Cada documento possui seu próprio stream 'doc-{document_id}' no Event Store,
    garantindo que centenas de documentos processem em paralelo com zero contenção
    de concorrência e replay O(1) nativo.
    """

    def __init__(self, id: UUID | None = None) -> None:
        super().__init__(id or uuid4())
        self.kb_id: UUID | None = None
        self.file_name: str = ""
        self.content_type: str = ""
        self.storage_path: str = ""
        self.source_type: DocumentSourceType = DocumentSourceType.DOCUMENT
        self.ingested_at: float = 0.0
        self.status: DocumentStatus = DocumentStatus.PENDING_UPLOAD
        self.enable_ocr: bool = False
        self.ocr_instructions: str | None = None
        self.byte_size: int = 0
        self.markdown_storage_path: str = ""
        self.markdown_preview: str = ""
        self.total_parents: int = 0
        self.total_children: int = 0
        self.chunks_summary: list[dict[str, Any]] = []
        self.node_count: int = 0
        self.edge_count: int = 0
        self.subgraph_storage_path: str | None = None
        self.extracted_graph: ExtractedGraph | None = None
        self.indexed_nodes_count: int = 0
        self.indexed_edges_count: int = 0
        self.error_step: str | None = None
        self.error_message: str | None = None
        self.metadata: dict[str, Any] = {}

    @classmethod
    def create(
        cls,
        document_id: UUID,
        kb_id: UUID,
        file_name: str,
        content_type: str,
        storage_path: str,
        enable_ocr: bool = False,
        ocr_instructions: str | None = None,
        source_type: DocumentSourceType | None = None,
        ingested_at: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "DocumentAggregate":
        doc = cls(id=document_id)
        resolved_source = source_type or DocumentSourceType.infer(
            file_name=file_name, content_type=content_type
        )
        resolved_ingested_at = ingested_at if ingested_at is not None else time.time()
        doc.record_event(
            DocumentAttachedEvent(
                aggregate_id=doc.id,
                aggregate_type="DocumentAggregate",
                document_id=doc.id,
                kb_id=kb_id,
                file_name=file_name,
                content_type=content_type,
                storage_path=storage_path,
                source_type=resolved_source,
                ingested_at=resolved_ingested_at,
                enable_ocr=enable_ocr,
                ocr_instructions=ocr_instructions,
                metadata=dict(metadata or {}),
            )
        )
        return doc

    def mark_stored(self, storage_path: str, byte_size: int) -> None:
        if self.status == DocumentStatus.DELETED:
            return
        self.record_event(
            DocumentStoredEvent(
                aggregate_id=self.id,
                aggregate_type="DocumentAggregate",
                document_id=self.id,
                kb_id=self.kb_id,
                storage_path=storage_path,
                byte_size=byte_size,
            )
        )

    def mark_parsed(self, markdown_storage_path: str, markdown_preview: str) -> None:
        if self.status == DocumentStatus.DELETED:
            return
        self.record_event(
            DocumentParsedToMarkdownEvent(
                aggregate_id=self.id,
                aggregate_type="DocumentAggregate",
                document_id=self.id,
                kb_id=self.kb_id,
                markdown_storage_path=markdown_storage_path,
                markdown_preview=markdown_preview,
            )
        )

    def mark_chunked(
        self,
        total_parents: int,
        total_children: int,
        chunks_summary: list[dict[str, Any]] | None = None,
    ) -> None:
        if self.status == DocumentStatus.DELETED:
            return
        self.record_event(
            DocumentChunkedEvent(
                aggregate_id=self.id,
                aggregate_type="DocumentAggregate",
                document_id=self.id,
                kb_id=self.kb_id,
                total_parents=total_parents,
                total_children=total_children,
                chunks_summary=chunks_summary or [],
            )
        )

    def mark_graph_extracted(
        self,
        node_count: int,
        edge_count: int,
        subgraph_storage_path: str | None = None,
        extracted_graph: ExtractedGraph | None = None,
    ) -> None:
        if self.status == DocumentStatus.DELETED:
            return
        self.record_event(
            GraphExtractedFromDocumentEvent(
                aggregate_id=self.id,
                aggregate_type="DocumentAggregate",
                document_id=self.id,
                kb_id=self.kb_id,
                node_count=node_count,
                edge_count=edge_count,
                subgraph_storage_path=subgraph_storage_path,
                extracted_graph=extracted_graph,
            )
        )

    def mark_knowledge_indexed(
        self,
        indexed_nodes: int,
        indexed_edges: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.status == DocumentStatus.DELETED:
            return
        doc_meta = metadata if metadata is not None else self.metadata
        self.record_event(
            DocumentKnowledgeIndexedEvent(
                aggregate_id=self.id,
                aggregate_type="DocumentAggregate",
                document_id=self.id,
                kb_id=self.kb_id,
                indexed_nodes_count=indexed_nodes,
                indexed_edges_count=indexed_edges,
                metadata=dict(doc_meta),
            )
        )

    def mark_processing_failed(
        self,
        step: str,
        error_message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.status == DocumentStatus.DELETED:
            return
        doc_meta = metadata if metadata is not None else self.metadata
        self.record_event(
            DocumentProcessingFailedEvent(
                aggregate_id=self.id,
                aggregate_type="DocumentAggregate",
                document_id=self.id,
                kb_id=self.kb_id,
                step=step,
                error_message=error_message,
                metadata=dict(doc_meta),
            )
        )

    def delete(self) -> None:
        if self.status == DocumentStatus.DELETED:
            return
        self.record_event(
            DocumentDeletedEvent(
                aggregate_id=self.id,
                aggregate_type="DocumentAggregate",
                document_id=self.id,
                kb_id=self.kb_id,
            )
        )

    # Handlers para mutação de estado via replay de eventos
    def _apply_document_attached_event(self, event: DocumentAttachedEvent) -> None:
        self.kb_id = event.kb_id
        self.file_name = event.file_name
        self.content_type = event.content_type
        self.storage_path = event.storage_path
        self.source_type = event.source_type
        self.ingested_at = event.ingested_at
        self.enable_ocr = event.enable_ocr
        self.ocr_instructions = event.ocr_instructions
        self.metadata = dict(event.metadata)
        self.status = DocumentStatus.PENDING_UPLOAD

    def _apply_document_stored_event(self, event: DocumentStoredEvent) -> None:
        self.status = DocumentStatus.UPLOADED
        self.storage_path = event.storage_path
        self.byte_size = event.byte_size
        if event.kb_id:
            self.kb_id = event.kb_id
        self.error_step = None
        self.error_message = None

    def _apply_document_parsed_to_markdown_event(
        self, event: DocumentParsedToMarkdownEvent
    ) -> None:
        self.status = DocumentStatus.PARSED
        self.markdown_storage_path = event.markdown_storage_path
        self.markdown_preview = event.markdown_preview
        if event.kb_id:
            self.kb_id = event.kb_id

    def _apply_document_chunked_event(self, event: DocumentChunkedEvent) -> None:
        self.status = DocumentStatus.CHUNKED
        self.total_parents = event.total_parents
        self.total_children = event.total_children
        self.chunks_summary = list(event.chunks_summary or [])
        if event.kb_id:
            self.kb_id = event.kb_id

    def _apply_graph_extracted_from_document_event(
        self, event: GraphExtractedFromDocumentEvent
    ) -> None:
        self.status = DocumentStatus.GRAPH_EXTRACTED
        self.node_count = event.node_count
        self.edge_count = event.edge_count
        self.subgraph_storage_path = event.subgraph_storage_path
        self.extracted_graph = event.extracted_graph
        if event.kb_id:
            self.kb_id = event.kb_id

    def _apply_document_knowledge_indexed_event(self, event: DocumentKnowledgeIndexedEvent) -> None:
        self.status = DocumentStatus.INDEXED
        self.indexed_nodes_count = event.indexed_nodes_count
        self.indexed_edges_count = event.indexed_edges_count
        if event.kb_id:
            self.kb_id = event.kb_id

    def _apply_document_processing_failed_event(self, event: DocumentProcessingFailedEvent) -> None:
        self.status = DocumentStatus.FAILED
        self.error_step = event.step
        self.error_message = event.error_message
        if event.kb_id:
            self.kb_id = event.kb_id

    def _apply_document_deleted_event(self, event: DocumentDeletedEvent) -> None:
        self.status = DocumentStatus.DELETED
