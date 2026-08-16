from dataclasses import dataclass

from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.modules.knowledge.application.sagas.document_ingestion_saga_coordinator import (
    DocumentIngestionSagaCoordinator,
)
from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.create_knowledge_base import (
    CreateKnowledgeBaseUseCase,
)
from src.modules.knowledge.application.use_cases.query_knowledge import (
    QueryKnowledgeUseCase,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_graph_and_vector_store import (
    InMemoryGraphAndVectorStore,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_object_storage import (
    InMemoryObjectStorage,
)
from src.modules.knowledge.infrastructure.adapters.simple_markdown_parser import (
    SimpleMarkdownParser,
)
from src.modules.knowledge.infrastructure.extractors.structured_pydantic_graph_extractor import (
    StructuredPydanticGraphExtractor,
)


@dataclass
class AppContainer:
    event_bus: InMemoryEventBus
    event_store: InMemoryEventStore
    kb_repository: InMemoryKnowledgeBaseRepository
    object_storage: InMemoryObjectStorage
    parser: SimpleMarkdownParser
    graph_extractor: StructuredPydanticGraphExtractor
    graph_vector_store: InMemoryGraphAndVectorStore
    saga_coordinator: DocumentIngestionSagaCoordinator
    create_kb_use_case: CreateKnowledgeBaseUseCase
    attach_doc_use_case: AttachAndStoreDocumentUseCase
    query_knowledge_use_case: QueryKnowledgeUseCase


def create_app_container() -> AppContainer:
    bus = InMemoryEventBus()
    store = InMemoryEventStore(event_bus=bus)
    repo = InMemoryKnowledgeBaseRepository()
    storage = InMemoryObjectStorage()
    parser = SimpleMarkdownParser()
    extractor = StructuredPydanticGraphExtractor()
    graph_store = InMemoryGraphAndVectorStore()

    saga = DocumentIngestionSagaCoordinator(
        event_bus=bus,
        event_store=store,
        kb_repository=repo,
        storage=storage,
        parser=parser,
        extractor=extractor,
        graph_store=graph_store,
        vector_store=graph_store,
    )

    create_kb = CreateKnowledgeBaseUseCase(store, repo)
    attach_doc = AttachAndStoreDocumentUseCase(store, repo, storage)
    query_kb = QueryKnowledgeUseCase(graph_store)

    return AppContainer(
        event_bus=bus,
        event_store=store,
        kb_repository=repo,
        object_storage=storage,
        parser=parser,
        graph_extractor=extractor,
        graph_vector_store=graph_store,
        saga_coordinator=saga,
        create_kb_use_case=create_kb,
        attach_doc_use_case=attach_doc,
        query_knowledge_use_case=query_kb,
    )
