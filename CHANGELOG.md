# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] - 2026-08-18

### Added
- **DeepSeek-V4-Flash Fact-Dense RAG Synthesizer (`DeepSeekRagSynthesizer`)**:
  - Novo adaptador de síntese RAG consumindo a API do OpenRouter (`deepseek/deepseek-v4-flash`) com temperatura determinística 0.1 e headers de governança.
  - Prompt estrito para Fact-Dense Markdown eliminando introduções/conclusões prolixas e exigindo citações diretas de nós e chunks (`[^chunk:<uuid>]`, `[^entidade:<tipo>:<nome>]`).
- **Arquitetura Dual-Mode de Consulta (`mode: "synthesis" | "retrieve"`)**:
  - Parâmetro `mode` em `QueryKnowledgeRequest` e `QueryKnowledgeDTO`.
  - Fast-Path `< 30ms` no `QueryKnowledgeUseCase` quando `mode == "retrieve"`, retornando imediatamente subgrafos e evidências para consumo por Tools de Agentes sem custo de LLM.
- **Frontend Query Playground Updates (`QueryPlaygroundView.tsx` & `AnswerView.tsx`)**:
  - Seletor interativo de modo de execução (`Síntese Fact-Dense (DeepSeek v4)` vs `Apenas Recuperação (Raw Fast-Path)`).
  - Atualização visual e tipográfica destacando o modelo DeepSeek-V4-Flash e proveniência estrita.

## [0.3.1] - 2026-08-18

### Added
- **CQRS Consolidated Read Model & Event-Driven Projections (`KnowledgeBaseProjector`)**:
  - Projector assíncrono escutando os 8 eventos de domínio do ciclo de vida da KB e sincronizando de forma idempotente as tabelas relacionais `knowledge_bases` e `attached_documents`.
  - Migration Alembic `0006_expand_attached_documents_read_model.py` expandindo a tabela de leitura com opções de OCR, contadores de chunks pai/filho, nós/arestas no FalkorDB e diagnósticos de erro.
  - Rotina de sincronização e backfill idempotente durante o bootstrap (`lifespan`) da API Gateway.
- **Repositório de Leitura O(1) com JOIN Ontológico (`PostgresKnowledgeBaseRepository`)**:
  - Consultas `get_by_id` e `list_all` executam `LEFT JOIN ontology_templates` para retornar o schema ontológico completo e métricas de documentos em tempo constante, sem necessidade de replay de eventos em requisições de leitura.
- **Frontend Pipeline Tracker & Card Ontológico**:
  - Correção do índice de conclusão no `PipelineStatusTracker.tsx`, exibindo checkmarks verdes em todas as etapas quando o status atinge `INDEXED`.
  - Card dedicado de **Ontologia Vinculada (Schema do Grafo)** na tela de detalhes da Knowledge Base (`KnowledgeBaseDetailPage.tsx`), com badges de entidades e relações.

## [0.3.0] - 2026-08-18

### Added
- **Configurable Multimodal OCR & OpenRouter Integration (`MarkItDownDocumentParser` & `OpenRouterClientFactory`)**:
  - **Fast-path Zero-Cost Default**: Plaintext and text-layer documents execute natively on CPU with zero LLM API calls and sub-second parsing speed.
  - **Multimodal Visual Analysis via OpenRouter**: Opt-in toggle to route image-heavy, diagrammatic, and scanned documents to `qwen/qwen3-vl-30b-a3b-instruct` (or configured VLM) through OpenRouter.
  - **Custom Markdown Structure Instructions (*Prompt Injection*)**: Upload request accepts custom formatting guidelines (e.g. strict GFM tables, mathematical preservation, standardized image annotations `> [Figura X: ...]`).
- **PydanticAI OpenRouter Responses Provider (`PydanticAiOpenRouterProviderFactory` & `PydanticAiGraphExtractor`)**:
  - Fábrica de modelos PydanticAI configurando `OpenAIResponsesModel` e `OpenAIProvider` com cliente `AsyncOpenAI` customizado.
  - Headers institucionais de governança (`HTTP-Referer`, `X-Title`) e controle deslizante de taxa de requisições via `RateLimitedAsyncTransport`.
  - Suporte ao modelo `deepseek/deepseek-v4-flash` para extração de grafos com alta precisão e baixo custo.
  - Fallback gracioso automático para extração determinística em cenários de indisponibilidade de rede ou ambientes de teste.
- **Backend API & Event Sourcing Updates**:
  - `POST /api/v1/knowledge/bases/{kb_id}/documents` accepts `enable_ocr: bool` and `ocr_instructions: str` via multipart form data.
  - `DocumentAttachedEvent` and `KnowledgeBaseAggregate` persist OCR preferences in event history.
  - `DocumentIngestionSagaCoordinator` propagates document OCR options to the parser step.
- **Frontend Console UI Enhancements**:
  - Added visual toggle in `DocumentUploadModal.tsx` for multimodal OCR with real-time fast-path zero-cost badge.
  - Added expandable textarea for optional Markdown structure instructions.
  - Updated API client and React Query hooks to transmit upload options seamlessly.

## [0.2.1] - 2026-08-17

### Added
- **Frontend Console SPA (`/frontend`)**:
  - Modern, responsive SPA built with **React 18.3.1 + Vite 5.4 + TypeScript 5.5 + Tailwind CSS 3.4** and TanStack React Query v5.
  - **Ontologies Hub**: Visual form to create and inspect domain schemas (entities, properties, relationships) and export JSON schemas.
  - **Knowledge Bases Hub**: Provisioning of KBs with ontology dropdown selector and inline creation modal.
  - **Document Ingestion & Live Pipeline Tracker**: Multi-file dropzone (PDF, TXT, MD, DOCX, JSON) with live visual Saga stage tracking (`Upload` ➔ `Parsing` ➔ `Chunking` ➔ `Grafo LLM` ➔ `Indexado`) and smart polling with auto-stop.
  - **RAG Query Playground**: Interactive query interface providing synthesized LLM answers via Gemini Flash-Lite paired with deep evidence inspection (retrieved chunks, relevance scores, and FalkorDB subgraphs/entities).
- **Backend RAG Synthesis & Listing Endpoints**:
  - `GET /api/v1/knowledge/bases`: Endpoint to list all Knowledge Bases with document metrics.
  - `POST /api/v1/knowledge/bases/{kb_id}/query`: Enriched with `ILlmSynthesisService` protocol (`GeminiRagSynthesizer` / `InMemoryRagSynthesizer`) generating grounded Markdown answers with factual citations.
- **Production Containerization**:
  - Multi-stage Dockerfile (`node:20-alpine` build + `nginx:1.27-alpine` runtime, image size < 25MB).
  - Added `frontend` service on port 3000 to `docker/docker-compose.yml` with SPA fallback and API reverse proxy.

## [0.2.0] - 2026-08-17

### Added
- **PydanticAI v2 Dynamic Graph Extractor (`PydanticAiGraphExtractor`)**:
  - Dynamically builds Pydantic models from user-defined `OntologySchema` at runtime.
  - Generates structured, strongly-typed JSON outputs using Google Gemini (`gemini-3.5-flash-lite`).
- **Transport-Level Rate Limiter (`RateLimitedAsyncTransport`)**:
  - Intercepts all outgoing HTTP transport requests with `AsyncTokenBucketLimiter`.
  - Non-blocking 60-second sliding window managing 300 RPM and 1.000.000 TPM with zero lock contention.
  - Automatic exponential backoff with full jitter for HTTP 429 (`ResourceExhausted`) responses.
- **Cumulative Canonical Entity Registry (`ExistingEntityRegistry`)**:
  - Caches and injects previously extracted entities per Knowledge Base into LLM extraction prompts to enforce entity ID reuse and eliminate cross-chunk duplication.
- **Universal Structure-Tolerant Markdown Chunker (`StructureTolerantMarkdownChunker`)**:
  - Uses `AtomicBlockLexer` to preserve tables, lists, and code blocks intact.
  - Emits contextual breadcrumb trails for Parent Chunks (~1.200 tokens) and overlapping Child Chunks (~200 tokens + 30 overlap).
- **High-Fidelity PDF Document Parsing (`MarkItDownDocumentParser`)**:
  - Added `markitdown[all]` support for robust PDF parsing with `pdfminer.six` and `pdfplumber`.
- **Parallelized Ingestion Saga Execution**:
  - Refactored `DocumentIngestionSagaCoordinator` with `asyncio.gather` for concurrent Parent Chunk processing bounded by `max_concurrency=15`.
- **Universal Brazilian Legal Ontology (`OntologiaJuridicaBrasileira`)**:
  - Modeled after LC 95/1998 with 7 core node types and 11 relationship types.
- **CLI Utility Scripts**:
  - `scripts/ingest_document.py`: Multi-format document ingestion pipeline CLI.
  - `scripts/register_legal_ontology.py`: Legal ontology registration CLI.
- **Architecture Decision Records (ADRs)**:
  - `ADR-0001: Hexagonal Event-Sourced Architecture with Single Class Per File`
  - `ADR-0002: Unified FalkorDB Hybrid GraphRAG Engine`
  - `ADR-0003: PydanticAI v2 Graph Extraction, Rate Limiting and Cumulative Canonization`
  - `ADR-0004: Universal Structure-Tolerant Markdown Chunker`
- **Real-World Document Benchmark**:
  - Successfully ingested and indexed the entire Brazilian Federal Constitution (CF/88, 437 pages, 1.34M characters, 293 Parent Chunks, 2.052 Child Chunks) into FalkorDB with verified sub-10ms hybrid search responses.

## [0.1.0] - 2026-08-16

### Added
- Unified FalkorDB Hybrid GraphRAG architecture with single-graph per Knowledge Base housing both structural document nodes (`:Document`, `:ParentChunk`, `:ChildChunk`) and ontological entity nodes (`:Entity`).
- Native FalkorDB HNSW vector index initialization (`ensure_vector_index`) on `(:ChildChunk.embedding)`.
- Structural document ingestion (`store_structural_document`) and parent-level conceptual mentions linking (`store_parent_mentions`) with `[:MENTIONS]` edges.
- Unified single-query OpenCypher hybrid search (`query_hybrid`) utilizing `db.idx.vector.queryNodes` with parent context ascension and connected entity expansion.
- Value objects `HybridSearchResult` and `StructuralGraphDocument` in `knowledge` domain.
- Centralized Settings and Secrets Management module (`AppSettings`) powered by `pydantic-settings` and `SecretStr`.
- Asynchronous database migration framework using Alembic and `asyncpg` (`make migrate`).
- Modular clean architecture with `kernel`, `knowledge`, and `api_gateway`.
- `kernel` domain primitives: `Entity`, `ValueObject`, `AggregateRoot`, `DomainEvent`, `DomainError`, and `Result[T, E]`.
- `kernel` application contracts: `UseCase`, `EventBus`, `EventStore`, and `Logger`.
- `kernel` infrastructure: `PostgresEventStore` with optimistic concurrency control and transactional locks.
- `knowledge` domain: `KnowledgeBase`, `Document`, `OntologyTemplate`, `OntologySchema`, `GraphNode`, `GraphEdge`.
- Dynamic ontology definitions with runtime Pydantic v2 validation (`DynamicOntologyModelBuilder`).
- Choreographed Event-Driven Ingestion Saga (`DocumentIngestionSagaCoordinator`) with Event Sourcing.
- `LocalFileSystemStorageAdapter` for partitioned asynchronous object storage with path traversal protection.
- `api_gateway` FastAPI REST endpoints for Ontology Templates, Knowledge Bases, Document Ingestion, and Knowledge Querying.
- Dependency injection container (`AppContainer`) supporting dynamic environment-based infrastructure selection.

### Removed
- Removed legacy `IVectorStore` interface and `PgVectorStoreAdapter` following unification of vector and graph queries directly in FalkorDB.
- Added Alembic migration `0004_drop_legacy_vector_tables.py` to drop redundant PostgreSQL tables `document_chunks` and `node_embeddings`.
- Unused dependencies `aioboto3` and `sqlalchemy` in favor of direct native `asyncpg` connection pooling.

### Verified
- Strict Mypy compliance (`strict = true`), 100% Ruff linting/formatting pass, and automated test coverage (93%+).
