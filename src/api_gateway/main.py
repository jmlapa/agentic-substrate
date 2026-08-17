from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api_gateway.container import AppContainer, create_app_container
from src.api_gateway.controllers.knowledge_controller import (
    router as knowledge_router,
)
from src.api_gateway.controllers.ontology_controller import ontology_router

container: AppContainer = create_app_container()
settings = container.settings

app = FastAPI(
    title=settings.api_title if settings else "Agentic Substrate API",
    description="Substrato modular para desenvolvimento agêntico com GraphRAG",
    version=settings.api_version if settings else "0.1.0",
    debug=settings.debug if settings else False,
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
