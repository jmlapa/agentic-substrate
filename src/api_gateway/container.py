from dataclasses import dataclass
from typing import Any

from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.infrastructure.app_settings import AppSettings
from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)
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
from src.modules.knowledge.application.use_cases.list_knowledge_bases import (
    ListKnowledgeBasesUseCase,
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
from src.modules.knowledge.domain.interfaces.i_llm_synthesis_service import (
    ILlmSynthesisService,
)
from src.modules.knowledge.domain.interfaces.i_markdown_chunker import (
    IMarkdownChunker,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)
from src.modules.knowledge.infrastructure.adapters.deepseek_rag_synthesizer import (
    DeepSeekRagSynthesizer,
)
from src.modules.knowledge.infrastructure.adapters.falkordb_graph_store_adapter import (
    FalkorDbGraphStoreAdapter,
)
from src.modules.knowledge.infrastructure.adapters.gemini_embedding_adapter import (
    GeminiEmbeddingAdapter,
)
from src.modules.knowledge.infrastructure.adapters.gemini_rag_synthesizer import (
    GeminiRagSynthesizer,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_embedding_service import (
    InMemoryEmbeddingService,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_graph_store import (
    InMemoryGraphStore,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_ontology_repository import (
    InMemoryOntologyRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_rag_synthesizer import (
    InMemoryRagSynthesizer,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.markitdown_document_parser import (
    MarkItDownDocumentParser,
)
from src.modules.knowledge.infrastructure.adapters.openrouter_client_factory import (
    OpenRouterClientFactory,
)
from src.modules.knowledge.infrastructure.adapters.postgres_knowledge_base_repository import (
    PostgresKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.postgres_ontology_repository import (
    PostgresOntologyRepository,
)
from src.modules.knowledge.infrastructure.chunking.structure_tolerant_markdown_chunker import (
    StructureTolerantMarkdownChunker,
)
from src.modules.knowledge.infrastructure.extractors.existing_entity_registry import (
    ExistingEntityRegistry,
)
from src.modules.knowledge.infrastructure.extractors.pydantic_ai_graph_extractor import (
    PydanticAiGraphExtractor,
)
from src.modules.knowledge.infrastructure.projections.knowledge_base_projector import (
    KnowledgeBaseProjector,
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
    synthesis_service: ILlmSynthesisService
    saga_coordinator: DocumentIngestionSagaCoordinator
    create_kb_use_case: CreateKnowledgeBaseUseCase
    list_kbs_use_case: ListKnowledgeBasesUseCase
    attach_doc_use_case: AttachAndStoreDocumentUseCase
    query_knowledge_use_case: QueryKnowledgeUseCase
    create_ontology_use_case: CreateOntologyTemplateUseCase
    get_ontology_use_case: GetOntologyTemplateUseCase
    list_ontologies_use_case: ListOntologyTemplatesUseCase
    projector: KnowledgeBaseProjector | None = None
    settings: AppSettings | None = None


def create_app_container(
    settings: AppSettings | None = None,
    storage_base_dir: str | None = None,
    graph_store_type: str | None = None,
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

    repo: IKnowledgeBaseRepository
    ontology_repo: IOntologyRepository
    if postgres_pool:
        repo = PostgresKnowledgeBaseRepository(pool=postgres_pool)
        ontology_repo = PostgresOntologyRepository(pool=postgres_pool)
    else:
        repo = InMemoryKnowledgeBaseRepository()
        ontology_repo = InMemoryOntologyRepository()

    # Object Storage (Local File System)
    base_dir = storage_base_dir or cfg.storage_local_base_dir
    storage: IObjectStorage = LocalFileSystemStorageAdapter(base_directory=base_dir)

    # Document Parser (MarkItDown with Fast-Path & OpenRouter Multimodal OCR)
    openrouter_key = cfg.openrouter_api_key.get_secret_value() if cfg.openrouter_api_key else None
    openrouter_client = OpenRouterClientFactory.create(
        api_key=openrouter_key,
        base_url=cfg.openrouter_base_url,
        app_title=cfg.openrouter_app_title,
        app_referer=cfg.openrouter_app_referer,
    )
    parser: IDocumentParser = MarkItDownDocumentParser(
        openrouter_client=openrouter_client,
        vision_model=cfg.ocr_vision_model_name,
        default_prompt=cfg.ocr_default_markdown_prompt,
    )

    # Markdown Chunker
    chunker: IMarkdownChunker = StructureTolerantMarkdownChunker()

    # Embedding Service (Gemini or InMemory)
    emb_type = embedding_service_type or cfg.embedding_service_type
    gemini_key = cfg.gemini_api_key.get_secret_value() if cfg.gemini_api_key else None
    embedding_service: IEmbeddingService
    if (emb_type == "gemini" or gemini_key) and gemini_key:
        dim = cfg.embedding_dimension
        embedding_service = GeminiEmbeddingAdapter(api_key=gemini_key, dimension=dim)
    else:
        embedding_service = InMemoryEmbeddingService()

    # Rate Limiter & Entity Registry
    limiter = AsyncTokenBucketLimiter(
        max_rpm=cfg.gemini_max_rpm,
        max_tpm=cfg.gemini_max_tpm,
    )
    entity_registry = ExistingEntityRegistry()

    # Graph Extractor (PydanticAI with OpenRouter or Gemini)
    extractor_provider = cfg.graph_extractor_provider
    extractor: IGraphExtractor
    if extractor_provider == "openrouter" and openrouter_key:
        extractor = PydanticAiGraphExtractor(
            rate_limiter=limiter,
            entity_registry=entity_registry,
            provider_type="openrouter",
            model_name=cfg.openrouter_graph_model_name,
            api_key=openrouter_key,
            base_url=cfg.openrouter_base_url,
            app_title=cfg.openrouter_app_title,
            app_referer=cfg.openrouter_app_referer,
            max_concurrency=cfg.gemini_max_concurrency,
        )
    else:
        extractor = PydanticAiGraphExtractor(
            rate_limiter=limiter,
            entity_registry=entity_registry,
            provider_type="gemini",
            model_name=cfg.gemini_model_name,
            api_key=gemini_key,
            max_concurrency=cfg.gemini_max_concurrency,
        )

    # Graph Store (FalkorDB or InMemory)
    grp_type = graph_store_type or cfg.graph_store_type
    graph_store: IGraphStore
    if grp_type == "falkordb":
        falkor_host = cfg.falkordb_host
        falkor_port = cfg.falkordb_port
        graph_store = FalkorDbGraphStoreAdapter(
            host=falkor_host, port=falkor_port, client=falkordb_client
        )
    else:
        graph_store = InMemoryGraphStore()

    # RAG Synthesis Service
    synthesis_service: ILlmSynthesisService
    if openrouter_key:
        synthesis_service = DeepSeekRagSynthesizer(
            api_key=openrouter_key,
            model_name=cfg.openrouter_synthesis_model_name,
            base_url=cfg.openrouter_base_url,
            max_tokens=cfg.openrouter_synthesis_max_tokens,
            app_title=cfg.openrouter_app_title,
            app_referer=cfg.openrouter_app_referer,
        )
    elif gemini_key:
        synthesis_service = GeminiRagSynthesizer(
            api_key=gemini_key,
            model_name=cfg.gemini_model_name,
        )
    else:
        synthesis_service = InMemoryRagSynthesizer()

    saga = DocumentIngestionSagaCoordinator(
        event_bus=bus,
        event_store=store,
        kb_repository=repo,
        storage=storage,
        parser=parser,
        extractor=extractor,
        graph_store=graph_store,
        chunker=chunker,
        embedding_service=embedding_service,
    )

    create_kb = CreateKnowledgeBaseUseCase(
        event_store=store,
        repository=repo,
        ontology_repository=ontology_repo,
    )
    list_kbs = ListKnowledgeBasesUseCase(repo)
    attach_doc = AttachAndStoreDocumentUseCase(store, repo, storage)
    query_kb = QueryKnowledgeUseCase(
        graph_store=graph_store,
        embedding_service=embedding_service,
        synthesis_service=synthesis_service,
    )

    create_ont = CreateOntologyTemplateUseCase(ontology_repo)
    get_ont = GetOntologyTemplateUseCase(ontology_repo)
    list_ont = ListOntologyTemplatesUseCase(ontology_repo)

    projector: KnowledgeBaseProjector | None = None
    if postgres_pool is not None:
        projector = KnowledgeBaseProjector(pool=postgres_pool, event_bus=bus)

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
        synthesis_service=synthesis_service,
        saga_coordinator=saga,
        create_kb_use_case=create_kb,
        list_kbs_use_case=list_kbs,
        attach_doc_use_case=attach_doc,
        query_knowledge_use_case=query_kb,
        create_ontology_use_case=create_ont,
        get_ontology_use_case=get_ont,
        list_ontologies_use_case=list_ont,
        projector=projector,
        settings=cfg,
    )
