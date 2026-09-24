from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api_gateway.container import AppContainer, create_app_container
from src.api_gateway.controllers.data_source_controller import (
    router as data_source_router,
)
from src.api_gateway.controllers.knowledge_controller import (
    router as knowledge_router,
)
from src.api_gateway.controllers.mcp_controller import router as mcp_router
from src.api_gateway.controllers.ontology_controller import ontology_router
from src.api_gateway.mcp.mcp_server_app import McpServerApplication
from src.kernel.infrastructure.app_settings import AppSettings

try:
    container: AppContainer = create_app_container(run_in_background=True)
except Exception:
    container = create_app_container(graph_store_type="in_memory", run_in_background=True)
settings = container.settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global container
    cfg = settings or AppSettings()
    pool: asyncpg.Pool | None = None
    try:
        password = cfg.postgres_password.get_secret_value() if cfg.postgres_password else None
        pool = await asyncpg.create_pool(
            host=cfg.postgres_host,
            port=cfg.postgres_port,
            user=cfg.postgres_user,
            password=password,
            database=cfg.postgres_db,
            min_size=10,
            max_size=40,
            timeout=20.0,
        )
    except Exception:
        pool = None

    import redis.asyncio as aioredis

    redis_client: Any | None = None
    try:
        redis_client = aioredis.from_url(
            f"redis://{cfg.redis_host}:{cfg.redis_port}/{cfg.redis_db}",
            decode_responses=False,
        )
    except Exception:
        redis_client = None

    container = create_app_container(
        settings=cfg,
        postgres_pool=pool,
        redis_client=redis_client,
        run_in_background=True,
    )
    app.state.container = container

    if pool and container.projector:
        try:
            async with pool.acquire() as conn:
                count = await conn.fetchval("SELECT count(*) FROM knowledge_bases")
                if count == 0:
                    streams = await conn.fetch("SELECT aggregate_id FROM event_streams")
                    for s in streams:
                        events = await container.event_store.get_events(s["aggregate_id"])
                        await container.projector.rebuild_projections_from_events(events)
        except Exception:
            pass

    # Inicia workers autônomos e watchdog de supervisão
    if container.ocr_worker:
        await container.ocr_worker.start()
    if container.graph_worker:
        await container.graph_worker.start()
    if container.ingestion_watchdog:
        await container.ingestion_watchdog.start()

    yield

    # Encerramento gracioso (Graceful Shutdown)
    if container.ingestion_watchdog:
        await container.ingestion_watchdog.stop()
    if container.graph_worker:
        await container.graph_worker.stop()
    if container.ocr_worker:
        await container.ocr_worker.stop()
    if redis_client:
        await getattr(redis_client, "aclose", redis_client.close)()
    if pool:
        await pool.close()


def create_app(container: AppContainer | None = None) -> FastAPI:
    cfg = container.settings if container else (settings or AppSettings())

    if container is not None:
        application = FastAPI(
            title=cfg.api_title if cfg else "Agentic Substrate API",
            description="Substrato modular para desenvolvimento agêntico com GraphRAG",
            version=cfg.api_version if cfg else "0.1.0",
            debug=cfg.debug if cfg else False,
        )
        application.state.container = container
    else:
        application = FastAPI(
            title=settings.api_title if settings else "Agentic Substrate API",
            description="Substrato modular para desenvolvimento agêntico com GraphRAG",
            version=settings.api_version if settings else "0.1.0",
            debug=settings.debug if settings else False,
            lifespan=lifespan,
        )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(knowledge_router)
    application.include_router(data_source_router)
    application.include_router(ontology_router)
    application.include_router(mcp_router)

    def get_active_container() -> AppContainer:
        if hasattr(application.state, "container") and application.state.container:
            return application.state.container  # type: ignore[no-any-return]
        if container is not None:
            return container
        from src.api_gateway.main import container as global_cnt

        return global_cnt

    mcp_app = McpServerApplication(container=get_active_container).create_app()
    application.mount("/mcp", mcp_app)

    @application.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "agentic-substrate"}

    return application


app = create_app()
