from src.api_gateway.controllers.knowledge_controller import (
    router as knowledge_router,
)
from src.api_gateway.controllers.mcp_controller import router as mcp_router
from src.api_gateway.controllers.ontology_controller import ontology_router

__all__ = ["knowledge_router", "mcp_router", "ontology_router"]
