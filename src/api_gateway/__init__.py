from src.api_gateway.container import AppContainer, create_app_container
from src.api_gateway.controllers.knowledge_controller import router as knowledge_router
from src.api_gateway.main import app

__all__ = ["AppContainer", "app", "create_app_container", "knowledge_router"]
