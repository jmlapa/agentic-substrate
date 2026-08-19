import tempfile
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from src.api_gateway.container import create_app_container
from src.kernel.infrastructure.app_settings import AppSettings
from src.modules.knowledge.domain.interfaces.i_document_parser import (
    IDocumentParser,
)
from src.modules.knowledge.infrastructure.adapters.falkordb_graph_store_adapter import (
    FalkorDbGraphStoreAdapter,
)
from src.modules.knowledge.infrastructure.adapters.gemini_embedding_adapter import (
    GeminiEmbeddingAdapter,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.parallel_vlm_document_parser import (
    ParallelVlmDocumentParser,
)


@pytest.mark.asyncio
async def test_container_creates_local_adapters_by_default() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        container = create_app_container(storage_base_dir=tmpdir)
        assert isinstance(container.object_storage, LocalFileSystemStorageAdapter)
        assert isinstance(container.parser, (ParallelVlmDocumentParser, IDocumentParser))


@pytest.mark.asyncio
async def test_container_creates_falkordb_adapter() -> None:
    mock_client = MagicMock()
    container = create_app_container(
        graph_store_type="falkordb",
        falkordb_client=mock_client,
    )
    assert isinstance(container.graph_store, FalkorDbGraphStoreAdapter)


@pytest.mark.asyncio
async def test_container_with_custom_app_settings() -> None:
    settings = AppSettings(
        ENVIRONMENT="test",
        STORAGE_LOCAL_BASE_DIR="/tmp/agentic-test-storage",
        GEMINI_API_KEY=SecretStr("mock-key-12345"),
        EMBEDDING_SERVICE_TYPE="gemini",
        EMBEDDING_DIMENSION=768,
    )
    container = create_app_container(settings=settings)
    assert container.settings is not None
    assert container.settings.environment == "test"
    assert isinstance(container.embedding_service, GeminiEmbeddingAdapter)


@pytest.mark.asyncio
async def test_container_creates_openrouter_synthesis_adapter() -> None:
    from src.modules.knowledge.infrastructure.adapters.openrouter_rag_synthesizer import (
        OpenRouterRagSynthesizer,
    )

    settings = AppSettings(
        OPENROUTER_API_KEY=SecretStr("mock-openrouter-key"),
        OPENROUTER_SYNTHESIS_MODEL_NAME="google/gemma-4-26b-a4b-it",
    )
    container = create_app_container(settings=settings)
    assert isinstance(container.synthesis_service, OpenRouterRagSynthesizer)


@pytest.mark.asyncio
async def test_container_creates_in_memory_job_queue_by_default() -> None:
    from src.kernel.infrastructure.in_memory_job_queue import InMemoryJobQueue

    container = create_app_container()
    assert isinstance(container.job_queue, InMemoryJobQueue)


@pytest.mark.asyncio
async def test_container_creates_redis_job_queue() -> None:
    from src.kernel.infrastructure.redis_job_queue import RedisJobQueue

    mock_redis = MagicMock()
    settings = AppSettings(JOB_QUEUE_TYPE="redis")
    container = create_app_container(settings=settings, redis_client=mock_redis)
    assert isinstance(container.job_queue, RedisJobQueue)
