# Spec: Database Versioned Migrations with Alembic

## Objective
Establish a robust, industry-standard, versioned database migration pipeline using **Alembic** configured for asynchronous execution with PostgreSQL (`asyncpg`) and `pgvector`. This replaces ad-hoc schema initialization in runtime code with deterministic, reproducible, forward-and-rollback capable database migrations for local development, CI/CD, and production environments.

## Tech Stack & Dependencies
- **Migration Tool:** `alembic>=1.13.0`
- **Driver / Engine:** `asyncpg>=0.29.0` via SQLAlchemy Core (`sqlalchemy[asyncio]>=2.0.30` used strictly for Alembic DDL migration runtime, application code remains native `asyncpg`).
- **Vector Support:** `pgvector>=0.3.0`

## Commands
```bash
# Apply all pending migrations to the latest revision
make migrate
# Or directly:
uv run alembic upgrade head

# Rollback one migration revision
make migrate-down
# Or directly:
uv run alembic downgrade -1

# Create a new revision file
make migrate-create name="create_knowledge_tables"
# Or directly:
uv run alembic revision -m "create_knowledge_tables"

# Check current database migration version
uv run alembic current

# Inspect migration history
uv run alembic history --verbose
```

## Project Structure
```
agentic-substrate/
├── alembic.ini                                # Alembic runtime configuration
├── migrations/
│   ├── env.py                                 # Async migration runner utilizing asyncpg connection url
│   ├── script.py.mako                         # Template for new revision files
│   └── versions/
│       ├── 0001_create_pgvector_extension.py   # Extension creation (CREATE EXTENSION IF NOT EXISTS vector)
│       ├── 0002_create_event_sourcing_tables.py # Kernel event sourcing (events, snapshots tables)
│       └── 0003_create_document_chunks_table.py # Knowledge module (document_chunks + HNSW index)
├── src/
│   ├── kernel/infrastructure/postgres_event_store.py  # Cleans up ad-hoc DDL
│   └── modules/knowledge/infrastructure/adapters/pgvector_store_adapter.py # Cleans up ad-hoc DDL
└── tests/
    └── integration/
        └── test_database_migrations.py        # Automated test verifying up & down cycles
```

## Migration Schemas (DDL Details)

### 1. Revision 0001: `pgvector` Extension
- **Upgrade:** `CREATE EXTENSION IF NOT EXISTS vector;`
- **Downgrade:** `DROP EXTENSION IF EXISTS vector;`

### 2. Revision 0002: Event Sourcing Tables (`kernel`)
- **Table `events`:**
  - `id`: BIGSERIAL PRIMARY KEY
  - `stream_id`: VARCHAR(255) NOT NULL
  - `stream_type`: VARCHAR(255) NOT NULL
  - `stream_position`: INTEGER NOT NULL
  - `event_type`: VARCHAR(255) NOT NULL
  - `event_data`: JSONB NOT NULL
  - `event_metadata`: JSONB NOT NULL
  - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()
  - Constraints & Indexes:
    - UNIQUE(`stream_id`, `stream_position`)
    - INDEX on `stream_id`
    - INDEX on `(stream_type, event_type)`
- **Table `snapshots`:**
  - `stream_id`: VARCHAR(255) PRIMARY KEY
  - `stream_type`: VARCHAR(255) NOT NULL
  - `stream_position`: INTEGER NOT NULL
  - `state`: JSONB NOT NULL
  - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()

### 3. Revision 0003: Document Chunks Table (`knowledge`)
- **Table `document_chunks`:**
  - `id`: VARCHAR(255) PRIMARY KEY
  - `document_id`: VARCHAR(255) NOT NULL
  - `knowledge_base_id`: VARCHAR(255) NOT NULL
  - `chunk_index`: INTEGER NOT NULL
  - `parent_id`: VARCHAR(255) NULL
  - `content`: TEXT NOT NULL
  - `breadcrumb`: VARCHAR(1000) NOT NULL DEFAULT ''
  - `token_count`: INTEGER NOT NULL DEFAULT 0
  - `embedding`: `VECTOR(768)` NULL
  - `metadata`: JSONB NOT NULL DEFAULT '{}'
  - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT NOW()
  - Indexes:
    - INDEX on `(knowledge_base_id, document_id)`
    - INDEX on `parent_id`
    - HNSW Vector Index:
      - `CREATE INDEX idx_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);`

## Testing Strategy
- Integration test suite running migrations:
  1. `alembic upgrade head` on test database/schema.
  2. Validate table structures and indexes exist.
  3. `alembic downgrade base` and verify clean rollback.
  4. Re-apply `alembic upgrade head` and verify idempotency.

## Boundaries
- **Always:** Use asynchronous migration execution (`run_migrations_online` with `asyncpg`).
- **Always:** Provide both `upgrade()` and `downgrade()` functions in every migration file.
- **Ask first:** Modifying or deleting existing published migration revisions.
- **Never:** Put application ORM business models in migrations (use explicit SQLAlchemy DDL expressions or raw SQL inside Alembic op execution).

## Success Criteria
- [ ] `alembic.ini` and `migrations/` directory scaffolded with async engine support.
- [ ] 3 initial versioned revisions created (`0001_create_pgvector_extension`, `0002_create_event_sourcing_tables`, `0003_create_document_chunks_table`).
- [ ] `Makefile` includes `migrate`, `migrate-down`, `migrate-create` commands.
- [ ] Adapters (`PostgresEventStore`, `PgVectorStoreAdapter`) clean of ad-hoc `CREATE TABLE` DDL while maintaining fallback/safe checks if needed.
- [ ] Tests and linter/typing gates pass with 0 errors (`make pre-commit`).
