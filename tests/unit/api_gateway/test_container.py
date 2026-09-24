from unittest.mock import MagicMock

import pytest

from src.api_gateway.container import create_app_container
from src.kernel.infrastructure.app_settings import AppSettings
from src.kernel.infrastructure.atomic_job_barrier import AtomicJobBarrier
from src.kernel.infrastructure.redis_stream_job_queue import RedisStreamJobQueue
from src.modules.knowledge.application.workers.graph_job_worker import GraphJobWorker
from src.modules.knowledge.application.workers.ingestion_watchdog import (
    IngestionWatchdog,
)
from src.modules.knowledge.application.workers.ocr_job_worker import OcrJobWorker
from src.modules.knowledge.infrastructure.adapters.postgres_document_repository import (
    PostgresDocumentRepository,
)


def test_create_app_container_defaults() -> None:
    settings = AppSettings()
    container = create_app_container(settings=settings)

    assert container is not None
    assert container.event_bus is not None
    assert container.event_store is not None
    assert container.kb_repository is not None
    assert container.document_repository is not None
    assert isinstance(container.document_repository, PostgresDocumentRepository)
    # Without redis_client, distributed stream workers are None
    assert container.stream_job_queue is None
    assert container.job_barrier is None
    assert container.ocr_worker is None
    assert container.graph_worker is None
    # Without postgres_pool, watchdog is None
    assert container.ingestion_watchdog is None


def test_create_app_container_with_redis_and_postgres() -> None:
    settings = AppSettings()
    mock_pool = MagicMock()
    mock_redis = MagicMock()

    container = create_app_container(
        settings=settings,
        postgres_pool=mock_pool,
        redis_client=mock_redis,
        run_in_background=False,
    )

    assert container is not None
    assert container.document_repository is not None
    assert isinstance(container.document_repository, PostgresDocumentRepository)
    assert container.stream_job_queue is not None
    assert isinstance(container.stream_job_queue, RedisStreamJobQueue)
    assert container.job_barrier is not None
    assert isinstance(container.job_barrier, AtomicJobBarrier)
    assert container.ocr_worker is not None
    assert isinstance(container.ocr_worker, OcrJobWorker)
    assert container.graph_worker is not None
    assert isinstance(container.graph_worker, GraphJobWorker)
    assert container.ingestion_watchdog is not None
    assert isinstance(container.ingestion_watchdog, IngestionWatchdog)


@pytest.mark.asyncio
async def test_fastapi_lifespan_lifecycle() -> None:
    from httpx import ASGITransport, AsyncClient

    from src.api_gateway.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "agentic-substrate"}
