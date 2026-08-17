# Spec: Settings and Secrets Management

## Objective
Establish a centralized, type-safe, and secure configuration and secrets management framework using **Pydantic Settings (`pydantic-settings`)**. This system replaces disparate `os.getenv()` calls across the application with validated configuration models, prevents accidental credential leakage via `SecretStr`, supports automated `.env` loading for containerized and local execution, and enables seamless dependency injection across application containers and database migration environments.

## Tech Stack & Dependencies
- **Pydantic Settings:** `pydantic-settings>=2.4.0` (already declared in `pyproject.toml`)
- **Pydantic v2 Core:** `pydantic>=2.8.0` (`SecretStr`, `Field`, `model_validator`)
- **Python:** 3.12+ (strictly typed with `mypy --strict`)

## Commands
```bash
# Run test suite including configuration tests
make test
# Or directly:
uv run pytest tests/unit/test_app_settings.py -v

# Run quality checks (Ruff linter/formatter + Mypy strict + Pytest)
make pre-commit
```

## Project Structure
```
agentic-substrate/
├── .env.example                                      # Documented sample environment variables template
├── src/
│   ├── kernel/
│   │   └── infrastructure/
│   │       ├── app_settings.py                       # Centralized AppSettings with SecretStr and computed properties
│   │       └── __init__.py                           # Export AppSettings
│   ├── api_gateway/
│   │   ├── container.py                              # AppContainer updated to accept and inject AppSettings
│   │   └── main.py                                   # FastAPI entrypoint consuming AppSettings
│   └── ...
├── migrations/
│   └── env.py                                        # Migrations runner consuming AppSettings database DSN
└── tests/
    └── unit/
        └── test_app_settings.py                      # Unit tests covering defaults, overrides, masking, and DSN generation
```

## Code Style & Implementation Details

### Configuration Model Architecture (`src/kernel/infrastructure/app_settings.py`)
```python
from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General Environment
    environment: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        alias="ENVIRONMENT",
    )
    debug: bool = Field(default=False, alias="DEBUG")

    # API & Service
    api_title: str = Field(default="Agentic Substrate API", alias="API_TITLE")
    api_version: str = Field(default="0.1.0", alias="API_VERSION")

    # LLM & Embeddings
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    embedding_service_type: Literal["memory", "gemini"] = Field(
        default="memory",
        alias="EMBEDDING_SERVICE_TYPE",
    )
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")

    # Database / Event Store / Vector Store
    event_store_type: Literal["memory", "postgres"] = Field(
        default="memory",
        alias="EVENT_STORE_TYPE",
    )
    vector_store_type: Literal["memory", "pgvector"] = Field(
        default="memory",
        alias="VECTOR_STORE_TYPE",
    )
    database_url: SecretStr | None = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(default=SecretStr("postgres"), alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="agentic_substrate", alias="POSTGRES_DB")

    # Graph Store (FalkorDB / RedisGraph)
    graph_store_type: Literal["memory", "falkordb"] = Field(
        default="memory",
        alias="GRAPH_STORE_TYPE",
    )
    falkordb_host: str = Field(default="localhost", alias="FALKORDB_HOST")
    falkordb_port: int = Field(default=6380, alias="FALKORDB_PORT")
    falkordb_password: SecretStr | None = Field(default=None, alias="FALKORDB_PASSWORD")

    # Object Storage
    storage_type: Literal["local", "s3"] = Field(default="local", alias="STORAGE_TYPE")
    storage_local_base_dir: str = Field(default="./data/storage", alias="STORAGE_LOCAL_BASE_DIR")
    s3_bucket_name: str | None = Field(default=None, alias="S3_BUCKET_NAME")
    s3_access_key_id: SecretStr | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: SecretStr | None = Field(default=None, alias="S3_SECRET_ACCESS_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")

    @property
    def postgres_asyncpg_dsn(self) -> str:
        if self.database_url:
            raw = self.database_url.get_secret_value()
            if raw.startswith("postgresql+asyncpg://"):
                return raw.replace("postgresql+asyncpg://", "postgresql://", 1)
            return raw
        pwd = self.postgres_password.get_secret_value()
        return f"postgresql://{self.postgres_user}:{pwd}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postgres_sqlalchemy_alembic_dsn(self) -> str:
        dsn = self.postgres_asyncpg_dsn
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql+asyncpg://", 1)
        elif dsn.startswith("postgresql://") and not dsn.startswith("postgresql+asyncpg://"):
            dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        return dsn
```

## Testing Strategy
- Unit tests in `tests/unit/test_app_settings.py`:
  1. Default initialization without environment variables.
  2. Loading from environment variables and `.env` dictionary mocks.
  3. Secret masking: ensuring `repr(settings)` and `settings.model_dump()` do not expose raw secret strings.
  4. Secret extraction: verifying `.get_secret_value()` returns raw keys when needed.
  5. Computed property tests: `postgres_asyncpg_dsn` and `postgres_sqlalchemy_alembic_dsn` handling both explicit `DATABASE_URL` and granular credentials.
  6. Integration validation: `create_app_container(settings=...)` and `migrations/env.py` integration without errors.

## Boundaries
- **Always:** Use `SecretStr` for API keys, database passwords, and cloud storage secret tokens.
- **Always:** Mask secrets in logs, representations, and serialization.
- **Always:** Adhere to `Single Class per File` rule (`AppSettings` in `app_settings.py`).
- **Ask first:** Adding new third-party cloud SDK integrations.
- **Never:** Commit raw secrets or non-template `.env` files with actual keys to version control.

## Success Criteria
- [ ] `AppSettings` implemented in `src/kernel/infrastructure/app_settings.py`.
- [ ] `.env.example` created at repository root with all environment variables documented.
- [ ] `AppContainer` refactored to consume `AppSettings` cleanly.
- [ ] `migrations/env.py` refactored to use `AppSettings` DSN resolution.
- [ ] Unit tests for `AppSettings` created with 100% pass rate.
- [ ] `make pre-commit` passes with 0 Ruff, Mypy, and Pytest errors.
