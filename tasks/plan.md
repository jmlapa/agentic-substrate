# Plan: Database Versioned Migrations with Alembic

## Architecture & Implementation Overview
This plan establishes Alembic as the official migration framework with async engine support (`asyncpg`) across kernel and knowledge modules.

```
alembic.ini ──> migrations/env.py (asyncpg) ──> migrations/versions/
                                                    ├── 0001_create_pgvector_extension.py
                                                    ├── 0002_create_event_sourcing_tables.py
                                                    └── 0003_create_document_chunks_table.py
```

## Phases & Execution Order

### Phase 1: Dependencies & Configuration
1. Add `alembic` and `sqlalchemy[asyncio]` to `pyproject.toml` and sync dependencies via `uv lock`.
2. Configure `alembic.ini` and `migrations/env.py` using `DATABASE_URL` / `POSTGRES_URL` env variables with `asyncio.run()` and `asyncpg` async connection.
3. Configure `migrations/script.py.mako` template.

### Phase 2: Revision Files Implementation
1. `0001_create_pgvector_extension.py`: Creates `vector` extension.
2. `0002_create_event_sourcing_tables.py`: Creates `events` (with unique constraint and indexes) and `snapshots` tables.
3. `0003_create_document_chunks_table.py`: Creates `document_chunks` table, composite index on `(knowledge_base_id, document_id)`, index on `parent_id`, and HNSW cosine vector index on `embedding vector(768)`.

### Phase 3: Makefile & Adapter Cleanup
1. Add `make migrate`, `make migrate-down`, `make migrate-create` targets to `Makefile`.
2. Refactor `PostgresEventStore` and `PgVectorStoreAdapter` to remove duplicate inline table creation queries while preserving connection assertions.

### Phase 4: Automated Verification
1. Create unit/integration tests for migration revision files and configuration.
2. Run `make pre-commit` (Ruff, Mypy, Pytest).
