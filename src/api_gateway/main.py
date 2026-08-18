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

container: AppContainer = create_app_container()
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
    )
    app.state.container = container
    yield
    if pool:
        await pool.close()


app = FastAPI(
    title=settings.api_title if settings else "Agentic Substrate API",
    description="Substrato modular para desenvolvimento agêntico com GraphRAG",
    version=settings.api_version if settings else "0.1.0",
    debug=settings.debug if settings else False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(knowledge_router)
app.include_router(ontology_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "agentic-substrate"}
