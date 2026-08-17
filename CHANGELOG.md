# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Asynchronous database migration framework using Alembic and `asyncpg` with CLI and Makefile automation (`make migrate`, `make migrate-down`, `make migrate-create`).
- Initial versioned migration revisions:
  - `0001_create_pgvector_extension.py`: Installs PostgreSQL `vector` extension.
  - `0002_create_event_sourcing_tables.py`: Creates `event_streams` and `domain_events` tables with concurrency constraints.
  - `0003_create_document_chunks_table.py`: Creates `node_embeddings` and `document_chunks` with HNSW cosine indexing.
- Recursive Markdown Structure-Aware Parent-Child Chunker (`MarkdownParentChildChunker`) with atomic table and code block preservation, breadcrumb generation, and recursive sub-splitting for large sections.
- Value objects `ParentChunk`, `ChildChunk`, and `DocumentChunkCollection` in `knowledge` domain.
- Google Gemini Embedding 2 adapter (`GeminiEmbeddingAdapter`) supporting MRL (768 dimensions), prompt task formatting, micro-batching of 100 items, and Exponential Backoff + Full Jitter for HTTP 429 (`ResourceExhausted`).
- Deterministic `InMemoryEmbeddingService` for local development and testing.
- `document_chunks` table and vector similarity methods (`store_document_chunks`, `search_similar_chunks`) with HNSW cosine indexing and document metadata filtering in `PgVectorStoreAdapter` and `InMemoryGraphAndVectorStore`.
- `DocumentChunkedEvent` and aggregate transition (`DocumentStatus.CHUNKED`) integrated into `DocumentIngestionSagaCoordinator`.
- Modular clean architecture with `kernel`, `knowledge`, and `api_gateway`.
- `kernel` domain primitives: `Entity`, `ValueObject`, `AggregateRoot`, `DomainEvent`, `DomainError`, and `Result[T, E]`.
- `kernel` application contracts: `UseCase`, `EventBus`, `EventStore`, and `Logger`.
- `kernel` infrastructure: `PostgresEventStore` with optimistic concurrency control and transactional locks.
- `knowledge` domain: `KnowledgeBase`, `Document`, `OntologyTemplate`, `OntologySchema`, `GraphNode`, `GraphEdge`.
- Dynamic ontology definitions with runtime Pydantic v2 validation (`DynamicOntologyModelBuilder`).
- Choreographed Event-Driven Ingestion Saga (`DocumentIngestionSagaCoordinator`) with Event Sourcing.
- `LocalFileSystemStorageAdapter` for partitioned asynchronous object storage with path traversal protection.
- `MarkItDownDocumentParser` for multi-format document-to-markdown conversion.
- `PgVectorStoreAdapter` with PostgreSQL 16 + pgvector cosine similarity search and HNSW indexing.
- `FalkorDbGraphStoreAdapter` with parameterized OpenCypher graph storage and subgraph querying.
- `api_gateway` FastAPI REST endpoints for Ontology Templates, Knowledge Bases, Document Ingestion, and Knowledge Querying.
- Dependency injection container (`AppContainer`) supporting dynamic environment-based infrastructure selection.

### Removed
- Obsolete `InMemoryObjectStorage` and `SimpleMarkdownParser` in favor of local production-grade adapters.
- Unused dependencies `aioboto3` (and its sub-dependencies `botocore`, `aiobotocore`, `s3transfer`) and `sqlalchemy` in favor of direct native `asyncpg` connection pooling.

### Verified
- Strict Mypy compliance (`strict = true`), 100% Ruff linting/formatting pass, and automated test coverage.
