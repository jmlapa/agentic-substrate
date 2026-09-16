import os
from collections.abc import Generator

import pytest

# Ensure environment variables are configured for test hermeticity before any module imports
os.environ["ENVIRONMENT"] = "test"
os.environ["EVENT_STORE_TYPE"] = "memory"
os.environ["GRAPH_STORE_TYPE"] = "memory"
os.environ["EMBEDDING_SERVICE_TYPE"] = "memory"
os.environ["STORAGE_LOCAL_BASE_DIR"] = "/tmp/agentic-test-storage"


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment() -> Generator[None, None, None]:
    """Ensure automated tests run in isolated in-memory mode by default."""
    yield
