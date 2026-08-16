# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Modular clean architecture with `kernel`, `knowledge`, and `api_gateway`.
- `kernel` primitives: `Entity`, `ValueObject`, `AggregateRoot`, `DomainEvent`, `DomainError`, and `Result[T, E]`.
- `kernel` application contracts: `UseCase`, `EventBus`, `EventStore`, and `Logger`.
- Dynamic ontology definitions for Knowledge Bases with runtime Pydantic validation (`DynamicOntologyModelBuilder`).
- Choreographed Event-Driven Ingestion Saga (`DocumentIngestionSagaCoordinator`) with Event Sourcing.
- Partitioned object storage adapters and in-memory graph/vector stores.
- FastAPI endpoints for KB creation, document upload, and subgraph/vector querying.
- Full Mypy strict mode, Ruff linting/formatting, and pytest test suite.
