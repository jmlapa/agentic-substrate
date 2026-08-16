# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

### Verified
- Strict Mypy compliance (`strict = true`), 100% Ruff linting/formatting pass, and automated test coverage.
