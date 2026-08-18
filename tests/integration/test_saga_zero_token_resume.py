import tempfile
from unittest.mock import AsyncMock

import pytest

from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.modules.knowledge.application.sagas.document_ingestion_saga_coordinator import (
    DocumentIngestionSagaCoordinator,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.events.document_progress_updated_event import (
    DocumentProgressUpdatedEvent,
)
from src.modules.knowledge.domain.events.document_stored_event import (
    DocumentStoredEvent,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
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
from src.modules.knowledge.infrastructure.adapters.page_checkpoint_storage import (
    PageCheckpointStorage,
)
from src.modules.knowledge.infrastructure.adapters.parent_graph_checkpoint_storage import (
    ParentGraphCheckpointStorage,
)


@pytest.mark.asyncio
async def test_saga_resumes_with_zero_token_waste_on_existing_checkpoints() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository()
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        page_checkpoint = PageCheckpointStorage(storage=storage)
        graph_checkpoint = ParentGraphCheckpointStorage(storage=storage)

        mock_parser = AsyncMock()
        mock_extractor = AsyncMock()
        graph_store = InMemoryGraphStore()
        embedding_service = InMemoryEmbeddingService(dimension=768)

        progress_events: list[DocumentProgressUpdatedEvent] = []

        async def capture_progress(event: object) -> None:
            if isinstance(event, DocumentProgressUpdatedEvent):
                progress_events.append(event)

        bus.subscribe(DocumentProgressUpdatedEvent, capture_progress)

        saga = DocumentIngestionSagaCoordinator(
            event_bus=bus,
            event_store=store,
            kb_repository=repo,
            storage=storage,
            parser=mock_parser,
            extractor=mock_extractor,
            graph_store=graph_store,
            embedding_service=embedding_service,
            page_checkpoint_storage=page_checkpoint,
            parent_graph_checkpoint_storage=graph_checkpoint,
        )

        kb = KnowledgeBaseAggregate.create(
            name="TestKB",
            description="Desc",
            ontology=OntologySchema(name="Onto", description="", node_types=[]),
        )
        await repo.save(kb)

        doc_id = kb.attach_document("test.pdf", "application/pdf")
        doc_info = kb.documents[doc_id]
        storage_path = doc_info["storage_path"]
        await storage.put_object(storage_path, b"%PDF-dummy", "application/pdf")
        kb.mark_document_stored(doc_id, storage_path, len(b"%PDF-dummy"))
        await repo.save(kb)
        await store.append_events(kb.id, "KnowledgeBaseAggregate", list(kb.uncommitted_events), 0)
        kb.mark_events_as_committed()

        # Configura o retorno do parser mockado
        mock_parser.parse_to_markdown.return_value = "# Title\n\n## Section 1\nSome paragraph text."

        # Dispara handle_document_stored
        event = DocumentStoredEvent(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            document_id=doc_id,
            storage_path=storage_path,
            byte_size=len(b"%PDF-dummy"),
        )
        await saga.handle_document_stored(event)

        # Valida que o parser foi chamado passando kb_partition e doc_id
        assert mock_parser.parse_to_markdown.called
        call_kwargs = mock_parser.parse_to_markdown.call_args[1]
        assert call_kwargs.get("doc_id") == doc_id
        assert call_kwargs.get("kb_partition") == kb.storage_partition
