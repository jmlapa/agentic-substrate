from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)


class CreateDataSourceRequest(BaseModel):
    kb_id: UUID = Field(..., description="ID da Base de Conhecimento associada")
    name: str = Field(..., description="Nome descritivo do DataSource")
    data_source_type: DataSourceType = Field(
        default=DataSourceType.GOOGLE_DRIVE_FOLDER,
        description="Tipo do conector da fonte de dados",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuração específica do conector",
    )
    sync_interval_minutes: int = Field(
        default=15,
        description="Intervalo em minutos para sincronizações automáticas",
    )
