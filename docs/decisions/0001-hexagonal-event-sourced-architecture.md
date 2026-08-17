# ADR-0001: Hexagonal Event-Sourced Architecture with Single Class Per File

## Status
Accepted

## Date
2026-08-16

## Context
The Agentic Substrate requires a robust, evolvable, and decoupled architectural foundation to support complex multi-agent workflows, knowledge graph pipelines, and asynchronous sagas. Key challenges included:
- Avoiding monolithic sprawl and tight coupling between domain business logic and external infrastructure (databases, LLMs, storage).
- Ensuring 100% auditability and complete historical reconstruction of knowledge bases and agent states.
- Enforcing strict code clarity, maintainability, and clean PR diffs for both human engineers and AI coding assistants.

## Decision
Adopt **Hexagonal Architecture (Ports and Adapters)** combined with **Event Sourcing** and strict **Single Class Per File** modularity:
1. **Domain Layer**: Contains pure business logic, entities, value objects, and domain events without external framework dependencies.
2. **Application Layer**: Contains use cases, sagas, and interface ports (`i_*.py`).
3. **Infrastructure Layer**: Contains concrete adapters for external services (PostgreSQL, FalkorDB, Gemini, FileSystem).
4. **Single Class Per File**: Every Entity, Value Object, DTO, Domain Event, Protocol, and Adapter resides in its own isolated `.py` file. `__init__.py` files act purely as public facades.
5. **PostgreSQL Event Store**: Implements optimistic concurrency control via sequence versions and transactional locking.

## Alternatives Considered

### Traditional CRUD with ORM (ActiveRecord / SQLAlchemy Models)
- **Pros**: Quick initial prototyping.
- **Cons**: State mutability leads to lost operational history, race conditions in distributed sagas, and tight coupling between database tables and business logic.
- **Rejected**: Insufficient auditability and resilience for multi-agent asynchronous pipelines.

### Monolithic File Modules
- **Pros**: Fewer files in the repository tree.
- **Cons**: High merge conflicts, degraded AI assistant context isolation, difficult unit testing.
- **Rejected**: Strict Single Class Per File delivers superior modularity and context window optimization.

## Consequences
- Every state mutation produces an immutable `DomainEvent` appended to `PostgresEventStore`.
- Full replayability and debugging of knowledge base aggregates.
- Strict type checking (`mypy --strict`) and zero cross-domain leakage.
