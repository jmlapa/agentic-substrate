from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_UNSET: object = object()


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
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
    gemini_model_name: str = Field(
        default="gemini-3.5-flash-lite",
        alias="GEMINI_MODEL_NAME",
    )
    gemini_max_rpm: int = Field(default=300, alias="GEMINI_MAX_RPM")
    gemini_max_tpm: int = Field(default=1_000_000, alias="GEMINI_MAX_TPM")
    gemini_max_concurrency: int = Field(default=15, alias="GEMINI_MAX_CONCURRENCY")
    embedding_service_type: Literal["memory", "gemini"] = Field(
        default="memory",
        alias="EMBEDDING_SERVICE_TYPE",
    )
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")

    # OpenRouter & Multimodal OCR / Graph Extraction
    openrouter_api_key: SecretStr | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_app_title: str = Field(
        default="Agentic Substrate",
        alias="OPENROUTER_APP_TITLE",
    )
    openrouter_app_referer: str = Field(
        default="https://agentic-substrate.local",
        alias="OPENROUTER_APP_REFERER",
    )
    graph_extractor_provider: Literal["gemini", "openrouter"] = Field(
        default="openrouter",
        alias="GRAPH_EXTRACTOR_PROVIDER",
    )
    openrouter_graph_model_name: str = Field(
        default="google/gemma-4-26b-a4b-it",
        alias="OPENROUTER_GRAPH_MODEL_NAME",
    )
    openrouter_synthesis_model_name: str = Field(
        default="google/gemma-4-26b-a4b-it",
        alias="OPENROUTER_SYNTHESIS_MODEL_NAME",
    )
    openrouter_synthesis_max_tokens: int = Field(
        default=800,
        alias="OPENROUTER_SYNTHESIS_MAX_TOKENS",
    )
    openrouter_max_rpm: int = Field(default=1500, alias="OPENROUTER_MAX_RPM")
    openrouter_max_tpm: int = Field(default=10_000_000, alias="OPENROUTER_MAX_TPM")
    openrouter_graph_max_concurrency: int = Field(
        default=50, alias="OPENROUTER_GRAPH_MAX_CONCURRENCY"
    )
    ocr_vision_model_name: str = Field(
        default="qwen/qwen3-vl-32b-instruct",
        alias="OCR_VISION_MODEL_NAME",
    )
    ocr_max_concurrency: int = Field(default=50, alias="OCR_MAX_CONCURRENCY")
    ocr_toc_batch_size: int = Field(default=25, alias="OCR_TOC_BATCH_SIZE")
    ocr_low_res_scale: float = Field(default=1.0, alias="OCR_LOW_RES_SCALE")
    ocr_high_res_scale: float = Field(default=2.0, alias="OCR_HIGH_RES_SCALE")
    ocr_default_markdown_prompt: str = Field(
        default=(
            "Transcribe document faithfully into GitHub Flavored Markdown. "
            "Preserve tables, headings and lists, and provide descriptive "
            "text for figures and diagrams."
        ),
        alias="OCR_DEFAULT_MARKDOWN_PROMPT",
    )

    # Database / Event Store
    event_store_type: Literal["memory", "postgres"] = Field(
        default="memory",
        alias="EVENT_STORE_TYPE",
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

    # Redis & Job Queue
    job_queue_type: Literal["memory", "redis"] = Field(
        default="memory",
        alias="JOB_QUEUE_TYPE",
    )
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: SecretStr | None = Field(default=None, alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    # Object Storage
    storage_type: Literal["local", "s3"] = Field(default="local", alias="STORAGE_TYPE")
    storage_local_base_dir: str = Field(default="./data/storage", alias="STORAGE_LOCAL_BASE_DIR")
    s3_bucket_name: str | None = Field(default=None, alias="S3_BUCKET_NAME")
    s3_access_key_id: SecretStr | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: SecretStr | None = Field(default=None, alias="S3_SECRET_ACCESS_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")

    def __init__(
        self,
        _env_file: Path | str | None | object = _UNSET,
        **values: Any,
    ) -> None:
        if _env_file is not _UNSET:
            super().__init__(_env_file=_env_file, **values)  # type: ignore[arg-type]
        else:
            super().__init__(**values)

    @property
    def postgres_asyncpg_dsn(self) -> str:
        if self.database_url:
            raw = self.database_url.get_secret_value()
            if raw.startswith("postgresql+asyncpg://"):
                return raw.replace("postgresql+asyncpg://", "postgresql://", 1)
            return raw
        pwd = self.postgres_password.get_secret_value()
        return (
            f"postgresql://{self.postgres_user}:{pwd}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_sqlalchemy_alembic_dsn(self) -> str:
        dsn = self.postgres_asyncpg_dsn
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql+asyncpg://", 1)
        elif dsn.startswith("postgresql://") and not dsn.startswith("postgresql+asyncpg://"):
            dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
        return dsn
