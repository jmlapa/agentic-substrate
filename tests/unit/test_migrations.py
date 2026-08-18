from alembic.config import Config
from alembic.script import ScriptDirectory

from migrations.env import get_database_url


def test_migrations_env_get_database_url_fallback() -> None:
    url = get_database_url()
    assert "postgresql+asyncpg://" in url


def test_migrations_env_get_database_url_normalization(monkeypatch: object) -> None:
    import os

    os.environ["DATABASE_URL"] = "postgres://user:pass@localhost:5432/mydb"
    assert get_database_url() == "postgresql+asyncpg://user:pass@localhost:5432/mydb"

    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/mydb"
    assert get_database_url() == "postgresql+asyncpg://user:pass@localhost:5432/mydb"

    os.environ.pop("DATABASE_URL", None)


def test_alembic_revisions_chain_is_unbroken() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    revisions = list(script.walk_revisions(base="base", head="head"))
    # Revisions are walked from head to base
    rev_ids = [rev.revision for rev in revisions]

    assert rev_ids == ["0006", "0005", "0004", "0003", "0002", "0001"]

    rev_0001 = script.get_revision("0001")
    assert rev_0001 is not None
    assert rev_0001.down_revision is None

    rev_0002 = script.get_revision("0002")
    assert rev_0002 is not None
    assert rev_0002.down_revision == "0001"

    rev_0003 = script.get_revision("0003")
    assert rev_0003 is not None
    assert rev_0003.down_revision == "0002"

    rev_0004 = script.get_revision("0004")
    assert rev_0004 is not None
    assert rev_0004.down_revision == "0003"

    rev_0005 = script.get_revision("0005")
    assert rev_0005 is not None
    assert rev_0005.down_revision == "0004"

    rev_0006 = script.get_revision("0006")
    assert rev_0006 is not None
    assert rev_0006.down_revision == "0005"
