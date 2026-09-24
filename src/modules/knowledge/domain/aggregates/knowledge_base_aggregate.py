import time
from typing import Any
from uuid import UUID, uuid4

from src.kernel.domain.aggregate_root import AggregateRoot
from src.modules.knowledge.domain.aggregates.document_aggregate import (
    DocumentAggregate,
)
from src.modules.knowledge.domain.events.document_attached_event import DocumentAttachedEvent
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
from src.modules.knowledge.domain.events.document_stored_event import DocumentStoredEvent
from src.modules.knowledge.domain.events.graph_extracted_from_document_event import (
    GraphExtractedFromDocumentEvent,
)
from src.modules.knowledge.domain.events.knowledge_base_created_event import (
    KnowledgeBaseCreatedEvent,
)
from src.modules.knowledge.domain.events.knowledge_base_deleted_event import (
    KnowledgeBaseDeletedEvent,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.document_source_type import (
    DocumentSourceType,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.knowledge_base_status import (
    KnowledgeBaseStatus,
)


class KnowledgeBaseAggregate(AggregateRoot):
    def __init__(self, id: UUID | None = None) -> None:
        super().__init__(id or uuid4())
        self.name: str = ""
        self.description: str = ""
        self.status: KnowledgeBaseStatus = KnowledgeBaseStatus.INITIALIZING
        self.ontology: OntologySchema | None = None
        self.storage_partition: str = ""
        self.documents: dict[UUID, dict[str, Any]] = {}

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        ontology: OntologySchema,
    ) -> "KnowledgeBaseAggregate":
        kb = cls()
        partition = f"kb-{kb.id}"
        kb.record_event(
            KnowledgeBaseCreatedEvent(
                aggregate_id=kb.id,
                aggregate_type="KnowledgeBaseAggregate",
                name=name,
                description=description,
                ontology=ontology,
                storage_partition=partition,
            )
        )
        return kb

    def create_document(
        self,
        file_name: str,
        content_type: str,
        enable_ocr: bool = False,
        ocr_instructions: str | None = None,
        source_type: DocumentSourceType | None = None,
        ingested_at: float | None = None,
        metadata: dict[str, Any] | None = None,
        document_id: UUID | None = None,
    ) -> DocumentAggregate:
        """
        Delega a criação e o ciclo de vida do documento para o DocumentAggregate autônomo.
        """
        doc_id = document_id or uuid4()
        storage_path = f"{self.storage_partition}/raw/{doc_id}-{file_name}"
        return DocumentAggregate.create(
            document_id=doc_id,
            kb_id=self.id,
            file_name=file_name,
            content_type=content_type,
            storage_path=storage_path,
            enable_ocr=enable_ocr,
            ocr_instructions=ocr_instructions,
            source_type=source_type,
            ingested_at=ingested_at,
            metadata=metadata,
        )

    def attach_document(
        self,
        file_name: str,
        content_type: str,
        enable_ocr: bool = False,
        ocr_instructions: str | None = None,
        source_type: DocumentSourceType | None = None,
        ingested_at: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        doc_id = uuid4()
        storage_path = f"{self.storage_partition}/raw/{doc_id}-{file_name}"
        resolved_source = source_type or DocumentSourceType.infer(
            file_name=file_name, content_type=content_type
        )
        resolved_ingested_at = ingested_at if ingested_at is not None else time.time()
        self.record_event(
            DocumentAttachedEvent(
                aggregate_id=self.id,
                aggregate_type="KnowledgeBaseAggregate",
                document_id=doc_id,
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
        return doc_id

    def mark_document_stored(self, document_id: UUID, storage_path: str, byte_size: int) -> None:
        self.record_event(
            DocumentStoredEvent(
                aggregate_id=self.id,
                aggregate_type="KnowledgeBaseAggregate",
                document_id=document_id,
                storage_path=storage_path,
                byte_size=byte_size,
            )
        )

    def mark_document_parsed(
        self, document_id: UUID, markdown_storage_path: str, markdown_preview: str
    ) -> None:
        self.record_event(
            DocumentParsedToMarkdownEvent(
                aggregate_id=self.id,
                aggregate_type="KnowledgeBaseAggregate",
                document_id=document_id,
                markdown_storage_path=markdown_storage_path,
                markdown_preview=markdown_preview,
            )
        )

    def mark_document_chunked(
        self,
        document_id: UUID,
        total_parents: int,
        total_children: int,
        chunks_summary: list[dict[str, Any]] | None = None,
    ) -> None:
        self.record_event(
            DocumentChunkedEvent(
                aggregate_id=self.id,
                aggregate_type="KnowledgeBaseAggregate",
                document_id=document_id,
                total_parents=total_parents,
                total_children=total_children,
                chunks_summary=chunks_summary or [],
            )
        )

    def mark_graph_extracted(self, document_id: UUID, extracted_graph: ExtractedGraph) -> None:
        self.record_event(
            GraphExtractedFromDocumentEvent(
                aggregate_id=self.id,
                aggregate_type="KnowledgeBaseAggregate",
                document_id=document_id,
                node_count=len(extracted_graph.nodes),
                edge_count=len(extracted_graph.edges),
                extracted_graph=extracted_graph,
            )
        )

    def mark_knowledge_indexed(
        self,
        document_id: UUID,
        indexed_nodes: int,
        indexed_edges: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        doc_meta = (
            metadata
            if metadata is not None
            else self.documents.get(document_id, {}).get("metadata", {})
        )
        self.record_event(
            DocumentKnowledgeIndexedEvent(
                aggregate_id=self.id,
                aggregate_type="KnowledgeBaseAggregate",
                document_id=document_id,
                indexed_nodes_count=indexed_nodes,
                indexed_edges_count=indexed_edges,
                metadata=dict(doc_meta),
            )
        )

    def mark_processing_failed(
        self,
        document_id: UUID,
        step: str,
        error_message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        doc_meta = (
            metadata
            if metadata is not None
            else self.documents.get(document_id, {}).get("metadata", {})
        )
        self.record_event(
            DocumentProcessingFailedEvent(
                aggregate_id=self.id,
                aggregate_type="KnowledgeBaseAggregate",
                document_id=document_id,
                step=step,
                error_message=error_message,
                metadata=dict(doc_meta),
            )
        )

    def remove_document(self, document_id: UUID) -> None:
        if document_id in self.documents:
            self.record_event(
                DocumentDeletedEvent(
                    aggregate_id=self.id,
                    aggregate_type="KnowledgeBaseAggregate",
                    document_id=document_id,
                )
            )

    def delete(self) -> None:
        self.record_event(
            KnowledgeBaseDeletedEvent(
                aggregate_id=self.id,
                aggregate_type="KnowledgeBaseAggregate",
            )
        )

    def _apply_knowledge_base_created_event(self, event: KnowledgeBaseCreatedEvent) -> None:
        self.name = event.name
        self.description = event.description
        self.ontology = event.ontology
        self.storage_partition = event.storage_partition
        self.status = KnowledgeBaseStatus.ACTIVE

    def _apply_knowledge_base_deleted_event(self, event: KnowledgeBaseDeletedEvent) -> None:
        self.status = KnowledgeBaseStatus.ARCHIVED
        self.documents.clear()

    def _apply_document_deleted_event(self, event: DocumentDeletedEvent) -> None:
        self.documents.pop(event.document_id, None)

    def _apply_document_attached_event(self, event: DocumentAttachedEvent) -> None:
        self.documents[event.document_id] = {
            "id": event.document_id,
            "file_name": event.file_name,
            "content_type": event.content_type,
            "storage_path": event.storage_path,
            "source_type": event.source_type,
            "ingested_at": event.ingested_at,
            "status": DocumentStatus.PENDING_UPLOAD,
            "enable_ocr": event.enable_ocr,
            "ocr_instructions": event.ocr_instructions,
            "metadata": event.metadata,
        }

    def _apply_document_stored_event(self, event: DocumentStoredEvent) -> None:
        if event.document_id in self.documents:
            self.documents[event.document_id]["status"] = DocumentStatus.UPLOADED
            self.documents[event.document_id]["byte_size"] = event.byte_size
            self.documents[event.document_id]["storage_path"] = event.storage_path
            self.documents[event.document_id]["error_step"] = None
            self.documents[event.document_id]["error_message"] = None
            self.documents[event.document_id]["error"] = None

    def _apply_document_parsed_to_markdown_event(
        self, event: DocumentParsedToMarkdownEvent
    ) -> None:
        if event.document_id in self.documents:
            self.documents[event.document_id]["status"] = DocumentStatus.PARSED
            self.documents[event.document_id]["markdown_path"] = event.markdown_storage_path

    def _apply_document_chunked_event(self, event: DocumentChunkedEvent) -> None:
        if event.document_id in self.documents:
            self.documents[event.document_id]["status"] = DocumentStatus.CHUNKED
            self.documents[event.document_id]["total_parents"] = event.total_parents
            self.documents[event.document_id]["total_children"] = event.total_children
            self.documents[event.document_id]["chunks_summary"] = event.chunks_summary or []

    def _apply_graph_extracted_from_document_event(
        self, event: GraphExtractedFromDocumentEvent
    ) -> None:
        if event.document_id in self.documents:
            self.documents[event.document_id]["status"] = DocumentStatus.GRAPH_EXTRACTED
            self.documents[event.document_id]["extracted_graph"] = event.extracted_graph
            self.documents[event.document_id]["node_count"] = event.node_count
            self.documents[event.document_id]["edge_count"] = event.edge_count

    def _apply_document_knowledge_indexed_event(self, event: DocumentKnowledgeIndexedEvent) -> None:
        if event.document_id in self.documents:
            self.documents[event.document_id]["status"] = DocumentStatus.INDEXED
            self.documents[event.document_id]["indexed_nodes_count"] = event.indexed_nodes_count
            self.documents[event.document_id]["indexed_edges_count"] = event.indexed_edges_count

    def _apply_document_processing_failed_event(self, event: DocumentProcessingFailedEvent) -> None:
        if event.document_id in self.documents:
            self.documents[event.document_id]["status"] = DocumentStatus.FAILED
            self.documents[event.document_id]["error"] = {
                "step": event.step,
                "message": event.error_message,
            }
