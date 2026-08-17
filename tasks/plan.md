# Plan: Centralized Settings and Secrets Management

## Architecture & Implementation Overview
This plan implements a type-safe settings and secrets management architecture using `pydantic-settings` within `src/kernel/infrastructure/app_settings.py`, providing masked secret handling (`SecretStr`), environment variable parsing, `.env` file support, and clean dependency injection into `AppContainer` and Alembic migrations.

```
.env / Environment Variables
            │
            ▼
    AppSettings (pydantic-settings & SecretStr)
            │
      ┌─────┴──────────────────┐
      ▼                        ▼
AppContainer            migrations/env.py
(Services & Adapters)   (Alembic Async Engine)
```

## Phases & Execution Order

### Phase 1: Core Settings Model & Template
1. Create `src/kernel/infrastructure/app_settings.py` containing `AppSettings` with fields for General, LLM/Embeddings, Database, FalkorDB, and Object Storage.
2. Export `AppSettings` in `src/kernel/infrastructure/__init__.py`.
3. Create documented `.env.example` at repository root with safe placeholder values.

### Phase 2: Container & Migrations Integration
1. Refactor `src/api_gateway/container.py` to accept `settings: AppSettings | None = None` and remove scattered `os.getenv()` calls.
2. Update `migrations/env.py` to utilize `AppSettings().postgres_sqlalchemy_alembic_dsn` for database URL resolution.
3. Update `src/api_gateway/main.py` if needed to pass initialized settings.

### Phase 3: Unit Tests & Verification
1. Create `tests/unit/test_app_settings.py` testing defaults, environment overrides, secret masking with `SecretStr`, and asyncpg/sqlalchemy DSN formatting.
2. Update existing integration/unit tests where container or migration DSNs are exercised.
3. Run `make pre-commit` (Ruff, Mypy strict, Pytest) and verify zero errors.
