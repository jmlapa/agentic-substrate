from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api_gateway.container import AppContainer, create_app_container
from src.api_gateway.controllers.knowledge_controller import (
    router as knowledge_router,
)
from src.api_gateway.controllers.ontology_controller import ontology_router
from src.kernel.infrastructure.app_settings import AppSettings

container: AppContainer = create_app_container(run_in_background=True)
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
            min_size=1,
            max_size=10,
            timeout=5.0,
        )
    except Exception:
        pool = None

    container = create_app_container(
        settings=cfg,
        postgres_pool=pool,
        run_in_background=True,
    )
    app.state.container = container

    if pool and container.projector:
        try:
            async with pool.acquire() as conn:
                streams = await conn.fetch("SELECT aggregate_id FROM event_streams")
                for s in streams:
                    events = await container.event_store.get_events(s["aggregate_id"])
                    await container.projector.rebuild_projections_from_events(events)
        except Exception:
            pass

    yield
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
    application.include_router(ontology_router)

    @application.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "agentic-substrate"}

    return application


app = create_app()
