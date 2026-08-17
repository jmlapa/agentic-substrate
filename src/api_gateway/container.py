from dataclasses import dataclass
from typing import Any

from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.infrastructure.app_settings import AppSettings
from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.kernel.infrastructure.postgres_event_store import PostgresEventStore
from src.modules.knowledge.application.sagas.document_ingestion_saga_coordinator import (
    DocumentIngestionSagaCoordinator,
)
from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.create_knowledge_base import (
    CreateKnowledgeBaseUseCase,
)
from src.modules.knowledge.application.use_cases.create_ontology_template import (
    CreateOntologyTemplateUseCase,
)
from src.modules.knowledge.application.use_cases.get_ontology_template import (
    GetOntologyTemplateUseCase,
)
from src.modules.knowledge.application.use_cases.list_ontology_templates import (
    ListOntologyTemplatesUseCase,
)
from src.modules.knowledge.application.use_cases.query_knowledge import (
    QueryKnowledgeUseCase,
)
from src.modules.knowledge.domain.interfaces.i_document_parser import IDocumentParser
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
from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)
from src.modules.knowledge.domain.interfaces.i_vector_store import IVectorStore
from src.modules.knowledge.infrastructure.adapters.falkordb_graph_store_adapter import (
    FalkorDbGraphStoreAdapter,
)
from src.modules.knowledge.infrastructure.adapters.gemini_embedding_adapter import (
    GeminiEmbeddingAdapter,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_embedding_service import (
    InMemoryEmbeddingService,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_graph_and_vector_store import (
    InMemoryGraphAndVectorStore,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_ontology_repository import (
    InMemoryOntologyRepository,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.markitdown_document_parser import (
    MarkItDownDocumentParser,
)
from src.modules.knowledge.infrastructure.adapters.pgvector_store_adapter import (
    PgVectorStoreAdapter,
)
from src.modules.knowledge.infrastructure.chunking.markdown_parent_child_chunker import (
    MarkdownParentChildChunker,
)
from src.modules.knowledge.infrastructure.extractors.structured_pydantic_graph_extractor import (
    StructuredPydanticGraphExtractor,
)


@dataclass
class AppContainer:
    event_bus: EventBus
    event_store: EventStore
    kb_repository: IKnowledgeBaseRepository
    ontology_repository: IOntologyRepository
    object_storage: IObjectStorage
    parser: IDocumentParser
    chunker: IMarkdownChunker
    embedding_service: IEmbeddingService
    graph_extractor: IGraphExtractor
    graph_store: IGraphStore
    vector_store: IVectorStore
    saga_coordinator: DocumentIngestionSagaCoordinator
    create_kb_use_case: CreateKnowledgeBaseUseCase
    attach_doc_use_case: AttachAndStoreDocumentUseCase
    query_knowledge_use_case: QueryKnowledgeUseCase
    create_ontology_use_case: CreateOntologyTemplateUseCase
    get_ontology_use_case: GetOntologyTemplateUseCase
    list_ontologies_use_case: ListOntologyTemplatesUseCase
    settings: AppSettings | None = None


def create_app_container(
    settings: AppSettings | None = None,
    storage_base_dir: str | None = None,
    graph_store_type: str | None = None,
    vector_store_type: str | None = None,
    event_store_type: str | None = None,
    embedding_service_type: str | None = None,
    postgres_pool: Any | None = None,
    falkordb_client: Any | None = None,
) -> AppContainer:
    cfg = settings or AppSettings()
    bus: EventBus = InMemoryEventBus()

    # Event Store
    evt_type = event_store_type or cfg.event_store_type
    store: EventStore
    if evt_type == "postgres" and postgres_pool:
        store = PostgresEventStore(pool=postgres_pool, event_bus=bus)
    else:
        store = InMemoryEventStore(event_bus=bus)

    repo: IKnowledgeBaseRepository = InMemoryKnowledgeBaseRepository()
    ontology_repo: IOntologyRepository = InMemoryOntologyRepository()

    # Object Storage (Local File System)
    base_dir = storage_base_dir or cfg.storage_local_base_dir
    storage: IObjectStorage = LocalFileSystemStorageAdapter(base_directory=base_dir)

    # Document Parser (MarkItDown)
    parser: IDocumentParser = MarkItDownDocumentParser()

    # Markdown Chunker
    chunker: IMarkdownChunker = MarkdownParentChildChunker()

    # Embedding Service (Gemini or InMemory)
    emb_type = embedding_service_type or cfg.embedding_service_type
    gemini_key = cfg.gemini_api_key.get_secret_value() if cfg.gemini_api_key else None
    embedding_service: IEmbeddingService
    if (emb_type == "gemini" or gemini_key) and gemini_key:
        dim = cfg.embedding_dimension
        embedding_service = GeminiEmbeddingAdapter(api_key=gemini_key, dimension=dim)
    else:
        embedding_service = InMemoryEmbeddingService()

    extractor: IGraphExtractor = StructuredPydanticGraphExtractor()

    # In-memory shared graph & vector fallback
    in_memory_graph_vector = InMemoryGraphAndVectorStore()

    # Graph Store
    grp_type = graph_store_type or cfg.graph_store_type
    graph_store: IGraphStore
    if grp_type == "falkordb":
        falkor_host = cfg.falkordb_host
        falkor_port = cfg.falkordb_port
        graph_store = FalkorDbGraphStoreAdapter(
            host=falkor_host, port=falkor_port, client=falkordb_client
        )
    else:
        graph_store = in_memory_graph_vector

    # Vector Store
    vec_type = vector_store_type or cfg.vector_store_type
    vector_store: IVectorStore
    if vec_type == "pgvector" and postgres_pool:
        vector_store = PgVectorStoreAdapter(pool=postgres_pool)
    else:
        vector_store = in_memory_graph_vector

    saga = DocumentIngestionSagaCoordinator(
        event_bus=bus,
        event_store=store,
        kb_repository=repo,
        storage=storage,
        parser=parser,
        extractor=extractor,
        graph_store=graph_store,
        vector_store=vector_store,
        chunker=chunker,
        embedding_service=embedding_service,
    )

    create_kb = CreateKnowledgeBaseUseCase(
        event_store=store,
        repository=repo,
        ontology_repository=ontology_repo,
    )
    attach_doc = AttachAndStoreDocumentUseCase(store, repo, storage)
    query_kb = QueryKnowledgeUseCase(graph_store)

    create_ont = CreateOntologyTemplateUseCase(ontology_repo)
    get_ont = GetOntologyTemplateUseCase(ontology_repo)
    list_ont = ListOntologyTemplatesUseCase(ontology_repo)

    return AppContainer(
        event_bus=bus,
        event_store=store,
        kb_repository=repo,
        ontology_repository=ontology_repo,
        object_storage=storage,
        parser=parser,
        chunker=chunker,
        embedding_service=embedding_service,
        graph_extractor=extractor,
        graph_store=graph_store,
        vector_store=vector_store,
        saga_coordinator=saga,
        create_kb_use_case=create_kb,
        attach_doc_use_case=attach_doc,
        query_knowledge_use_case=query_kb,
        create_ontology_use_case=create_ont,
        get_ontology_use_case=get_ont,
        list_ontologies_use_case=list_ont,
        settings=cfg,
    )
