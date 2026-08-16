from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api_gateway.container import AppContainer, create_app_container
from src.api_gateway.controllers.knowledge_controller import (
    router as knowledge_router,
)

container: AppContainer = create_app_container()

app = FastAPI(
    title="Agentic Substrate API",
    description="Substrato modular para desenvolvimento agêntico com GraphRAG",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(knowledge_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "agentic-substrate"}
