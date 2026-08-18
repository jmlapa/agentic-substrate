from uuid import UUID

import asyncpg

from src.kernel.application.event_bus import EventBus
from src.kernel.domain.domain_event import DomainEvent
from src.modules.knowledge.domain.events.document_attached_event import (
    DocumentAttachedEvent,
)
from src.modules.knowledge.domain.events.document_chunked_event import (
    DocumentChunkedEvent,
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
from src.modules.knowledge.domain.events.document_stored_event import DocumentStoredEvent
from src.modules.knowledge.domain.events.graph_extracted_from_document_event import (
    GraphExtractedFromDocumentEvent,
)
from src.modules.knowledge.domain.events.knowledge_base_created_event import (
    KnowledgeBaseCreatedEvent,
)


class KnowledgeBaseProjector:
    """
    Projector assíncrono para consolidação do Read Model no PostgreSQL (CQRS).
    Assina eventos de domínio do EventBus e projeta o estado desnormalizado
    nas tabelas relacionais 'knowledge_bases' e 'attached_documents'.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        event_bus: EventBus | None = None,
    ) -> None:
        self._pool = pool
        self._bus = event_bus
        if self._bus is not None:
            self._register_listeners(self._bus)

    def _register_listeners(self, bus: EventBus) -> None:
        bus.subscribe(KnowledgeBaseCreatedEvent, self.handle_knowledge_base_created)
        bus.subscribe(DocumentAttachedEvent, self.handle_document_attached)
        bus.subscribe(DocumentStoredEvent, self.handle_document_stored)
        bus.subscribe(DocumentProgressUpdatedEvent, self.handle_document_progress_updated)
        bus.subscribe(DocumentParsedToMarkdownEvent, self.handle_document_parsed)
        bus.subscribe(DocumentChunkedEvent, self.handle_document_chunked)
        bus.subscribe(GraphExtractedFromDocumentEvent, self.handle_graph_extracted)
        bus.subscribe(DocumentKnowledgeIndexedEvent, self.handle_document_indexed)
        bus.subscribe(DocumentProcessingFailedEvent, self.handle_document_failed)

    async def project_event(self, event: DomainEvent) -> None:
        if isinstance(event, KnowledgeBaseCreatedEvent):
            await self.handle_knowledge_base_created(event)
        elif isinstance(event, DocumentAttachedEvent):
            await self.handle_document_attached(event)
        elif isinstance(event, DocumentStoredEvent):
            await self.handle_document_stored(event)
        elif isinstance(event, DocumentProgressUpdatedEvent):
            await self.handle_document_progress_updated(event)
        elif isinstance(event, DocumentParsedToMarkdownEvent):
            await self.handle_document_parsed(event)
        elif isinstance(event, DocumentChunkedEvent):
            await self.handle_document_chunked(event)
        elif isinstance(event, GraphExtractedFromDocumentEvent):
            await self.handle_graph_extracted(event)
        elif isinstance(event, DocumentKnowledgeIndexedEvent):
            await self.handle_document_indexed(event)
        elif isinstance(event, DocumentProcessingFailedEvent):
            await self.handle_document_failed(event)

    async def handle_knowledge_base_created(self, event: DomainEvent) -> None:
        if not isinstance(event, KnowledgeBaseCreatedEvent):
            return

        ontology_id: UUID | None = None
        async with self._pool.acquire() as conn:
            # Tenta resolver o ontology_id pelo nome da ontologia caso exista template
            if event.ontology and event.ontology.name:
                row = await conn.fetchrow(
                    "SELECT id FROM ontology_templates WHERE name = $1 LIMIT 1",
                    event.ontology.name,
                )
                if row:
                    ontology_id = row["id"]

            query = """
            INSERT INTO knowledge_bases (
                id, name, description, status, storage_partition, ontology_id, updated_at
            ) VALUES (
                $1, $2, $3, 'ACTIVE', $4, $5, NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                status = EXCLUDED.status,
                storage_partition = EXCLUDED.storage_partition,
                ontology_id = COALESCE(EXCLUDED.ontology_id, knowledge_bases.ontology_id),
                updated_at = NOW();
            """
            await conn.execute(
                query,
                event.aggregate_id,
                event.name,
                event.description,
                event.storage_partition,
                ontology_id,
            )

    async def handle_document_attached(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentAttachedEvent):
            return

        query = """
        INSERT INTO attached_documents (
            id, kb_id, file_name, status, storage_path, enable_ocr, ocr_instructions, updated_at
        ) VALUES (
            $1, $2, $3, 'PENDING_UPLOAD', $4, $5, $6, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            file_name = EXCLUDED.file_name,
            storage_path = EXCLUDED.storage_path,
            enable_ocr = EXCLUDED.enable_ocr,
            ocr_instructions = EXCLUDED.ocr_instructions,
            updated_at = NOW();
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                event.document_id,
                event.aggregate_id,
                event.file_name,
                event.storage_path,
                event.enable_ocr,
                event.ocr_instructions,
            )

    async def handle_document_stored(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentStoredEvent):
            return

        query = """
        UPDATE attached_documents
        SET status = 'UPLOADED',
            error_step = NULL,
            error_message = NULL,
            storage_path = $1,
            updated_at = NOW()
        WHERE id = $2;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, event.storage_path, event.document_id)

    async def handle_document_progress_updated(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentProgressUpdatedEvent):
            return

        query = """
        UPDATE attached_documents
        SET status = CASE WHEN status = 'FAILED' THEN 'PROCESSING' ELSE status END,
            error_step = NULL,
            error_message = NULL,
            progress_step = $1::varchar,
            progress_current = $2::integer,
            progress_total = $3::integer,
            progress_percentage = CASE
                WHEN progress_step = $1::varchar THEN
                    GREATEST(COALESCE(progress_percentage, 0), $4::integer)
                ELSE $4::integer
            END,
            progress_message = $5::text,
            updated_at = NOW()
        WHERE id = $6::uuid;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                event.step,
                event.current,
                event.total,
                event.percentage,
                event.message,
                event.document_id,
            )

    async def handle_document_parsed(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentParsedToMarkdownEvent):
            return

        query = """
        UPDATE attached_documents
        SET status = 'PARSED',
            progress_step = 'CHUNKING',
            progress_current = 0,
            progress_total = 1,
            progress_percentage = 0,
            progress_message = 'Fatiando documento em Chunks Hierárquicos (Pai/Filho)...',
            updated_at = NOW()
        WHERE id = $1;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, event.document_id)

    async def handle_document_chunked(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentChunkedEvent):
            return

        query = """
        UPDATE attached_documents
        SET status = 'CHUNKED',
            total_parents = $1,
            total_children = $2,
            progress_step = 'EMBEDDINGS',
            progress_current = 0,
            progress_total = $2,
            progress_percentage = 0,
            progress_message = 'Iniciando geração de representações vetoriais...',
            updated_at = NOW()
        WHERE id = $3;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                event.total_parents,
                event.total_children,
                event.document_id,
            )

    async def handle_graph_extracted(self, event: DomainEvent) -> None:
        if not isinstance(event, GraphExtractedFromDocumentEvent):
            return

        query = """
        UPDATE attached_documents
        SET status = 'GRAPH_EXTRACTED',
            progress_step = 'INDEXING',
            progress_current = 0,
            progress_total = 1,
            progress_percentage = 0,
            progress_message = 'Indexando nós e arestas no FalkorDB...',
            updated_at = NOW()
        WHERE id = $1;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, event.document_id)

    async def handle_document_indexed(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentKnowledgeIndexedEvent):
            return

        query = """
        UPDATE attached_documents
        SET status = 'INDEXED',
            indexed_nodes_count = $1,
            indexed_edges_count = $2,
            progress_step = 'INDEXED',
            progress_current = 1,
            progress_total = 1,
            progress_percentage = 100,
            progress_message = 'Processamento e indexação concluídos com sucesso',
            updated_at = NOW()
        WHERE id = $3;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                event.indexed_nodes_count,
                event.indexed_edges_count,
                event.document_id,
            )

    async def handle_document_failed(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentProcessingFailedEvent):
            return

        query = """
        UPDATE attached_documents
        SET status = 'FAILED',
            error_step = $1,
            error_message = $2,
            updated_at = NOW()
        WHERE id = $3;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                event.step,
                event.error_message,
                event.document_id,
            )

    async def rebuild_projections_from_events(self, events: list[DomainEvent]) -> None:
        """
        Reprocessa uma lista cronológica de eventos para reconstruir/reparar
        o Read Model consolidado.
        """
        for event in events:
            await self.project_event(event)
