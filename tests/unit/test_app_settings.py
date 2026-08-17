import os
from pathlib import Path

import pytest
from pydantic import SecretStr

from src.kernel.infrastructure.app_settings import AppSettings


def test_app_settings_defaults() -> None:
    settings = AppSettings()
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.api_title == "Agentic Substrate API"
    assert settings.api_version == "0.1.0"
    assert settings.embedding_service_type == "memory"
    assert settings.embedding_dimension == 768
    assert settings.event_store_type == "memory"
    assert settings.vector_store_type == "memory"
    assert settings.graph_store_type == "memory"
    assert settings.storage_type == "local"
    assert settings.storage_local_base_dir == "./data/storage"
    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432
    assert settings.postgres_user == "postgres"
    assert settings.postgres_password.get_secret_value() == "postgres"
    assert settings.postgres_db == "agentic_substrate"


def test_app_settings_secret_masking() -> None:
    settings = AppSettings(
        GEMINI_API_KEY=SecretStr("super-secret-gemini-key"),
        POSTGRES_PASSWORD=SecretStr("super-secret-pg-pass"),
        FALKORDB_PASSWORD=SecretStr("super-secret-falkor-pass"),
        S3_SECRET_ACCESS_KEY=SecretStr("super-secret-s3-pass"),
    )

    # String and repr representations must mask secrets
    settings_repr = repr(settings)
    assert "super-secret-gemini-key" not in settings_repr
    assert "super-secret-pg-pass" not in settings_repr
    assert "super-secret-falkor-pass" not in settings_repr
    assert "super-secret-s3-pass" not in settings_repr
    assert "**********" in settings_repr

    # Values must be accessible explicitly via get_secret_value()
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "super-secret-gemini-key"
    assert settings.postgres_password.get_secret_value() == "super-secret-pg-pass"
    assert settings.falkordb_password is not None
    assert settings.falkordb_password.get_secret_value() == "super-secret-falkor-pass"
    assert settings.s3_secret_access_key is not None
    assert settings.s3_secret_access_key.get_secret_value() == "super-secret-s3-pass"


def test_app_settings_environment_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        os,
        "environ",
        {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "EMBEDDING_SERVICE_TYPE": "gemini",
            "EMBEDDING_DIMENSION": "1536",
            "GEMINI_API_KEY": "ai-studio-prod-key",
            "POSTGRES_HOST": "postgres.internal",
            "POSTGRES_PORT": "5433",
            "POSTGRES_USER": "prod_user",
            "POSTGRES_PASSWORD": "prod_password",
            "POSTGRES_DB": "prod_db",
            "FALKORDB_HOST": "falkordb.internal",
            "FALKORDB_PORT": "6379",
            "STORAGE_TYPE": "s3",
            "S3_BUCKET_NAME": "my-prod-bucket",
        },
    )

    settings = AppSettings()
    assert settings.environment == "production"
    assert settings.debug is True
    assert settings.embedding_service_type == "gemini"
    assert settings.embedding_dimension == 1536
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "ai-studio-prod-key"
    assert settings.postgres_host == "postgres.internal"
    assert settings.postgres_port == 5433
    assert settings.postgres_user == "prod_user"
    assert settings.postgres_password.get_secret_value() == "prod_password"
    assert settings.postgres_db == "prod_db"
    assert settings.falkordb_host == "falkordb.internal"
    assert settings.falkordb_port == 6379
    assert settings.storage_type == "s3"
    assert settings.s3_bucket_name == "my-prod-bucket"


def test_app_settings_dsn_computation_granular() -> None:
    settings = AppSettings(
        POSTGRES_HOST="db.prod.lan",
        POSTGRES_PORT=5432,
        POSTGRES_USER="app_user",
        POSTGRES_PASSWORD=SecretStr("secret_pass"),
        POSTGRES_DB="app_database",
    )

    assert settings.postgres_asyncpg_dsn == (
        "postgresql://app_user:secret_pass@db.prod.lan:5432/app_database"
    )
    assert settings.postgres_sqlalchemy_alembic_dsn == (
        "postgresql+asyncpg://app_user:secret_pass@db.prod.lan:5432/app_database"
    )


def test_app_settings_dsn_computation_with_database_url_override() -> None:
    settings = AppSettings(DATABASE_URL=SecretStr("postgresql+asyncpg://usr:pwd@host:5432/mydb"))
    assert settings.postgres_asyncpg_dsn == "postgresql://usr:pwd@host:5432/mydb"
    assert settings.postgres_sqlalchemy_alembic_dsn == "postgresql+asyncpg://usr:pwd@host:5432/mydb"

    settings_simple = AppSettings(DATABASE_URL=SecretStr("postgres://usr:pwd@host:5432/mydb"))
    assert settings_simple.postgres_asyncpg_dsn == "postgres://usr:pwd@host:5432/mydb"
    assert (
        settings_simple.postgres_sqlalchemy_alembic_dsn
        == "postgresql+asyncpg://usr:pwd@host:5432/mydb"
    )


def test_app_settings_loads_from_custom_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "ENVIRONMENT=staging\n"
        "GEMINI_API_KEY=custom-env-file-gemini-key\n"
        "STORAGE_LOCAL_BASE_DIR=/custom/storage/path\n",
        encoding="utf-8",
    )

    settings = AppSettings(_env_file=str(env_file))
    assert settings.environment == "staging"
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "custom-env-file-gemini-key"
    assert settings.storage_local_base_dir == "/custom/storage/path"
