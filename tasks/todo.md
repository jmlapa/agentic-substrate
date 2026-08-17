# Tasks: Database Versioned Migrations with Alembic

- [ ] Task 1: Add dependencies & Alembic async configuration
  - Acceptance: `alembic` and `sqlalchemy` added to `pyproject.toml`, `uv.lock` resolved, `alembic.ini` and `migrations/env.py` configured with `asyncpg` async engine.
  - Verify: `uv run alembic current` runs without syntax or configuration errors.
  - Files: `pyproject.toml`, `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`

- [ ] Task 2: Implement initial migration revisions (0001, 0002, 0003)
  - Acceptance: 3 revision files generated covering `vector` extension, event sourcing tables (`events`, `snapshots`), and `document_chunks` table with HNSW index.
  - Verify: `uv run alembic check` / revision validation passes.
  - Files: `migrations/versions/0001_create_pgvector_extension.py`, `migrations/versions/0002_create_event_sourcing_tables.py`, `migrations/versions/0003_create_document_chunks_table.py`

- [ ] Task 3: Add Makefile targets and refactor adapters
  - Acceptance: `Makefile` updated with `migrate`, `migrate-down`, `migrate-create` commands; `PostgresEventStore` and `PgVectorStoreAdapter` refactored.
  - Verify: `make migrate` works or help targets execute cleanly.
  - Files: `Makefile`, `src/kernel/infrastructure/postgres_event_store.py`, `src/modules/knowledge/infrastructure/adapters/pgvector_store_adapter.py`

- [ ] Task 4: Automated tests and quality gate validation
  - Acceptance: Tests verify migration structure and revision chain; full `make pre-commit` passes with 0 errors.
  - Verify: `make pre-commit` succeeds.
  - Files: `tests/unit/test_migrations.py`
