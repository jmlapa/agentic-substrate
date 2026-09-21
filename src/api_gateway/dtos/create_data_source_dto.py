from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)


class CreateDataSourceDTO(BaseModel):
    name: str = Field(..., min_length=1, description="Nome descritivo do DataSource")
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
        ge=1,
        description="Intervalo em minutos para sincronizações automáticas",
    )

    @field_validator("data_source_type", mode="before")
    @classmethod
    def parse_data_source_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            for member in DataSourceType:
                if member.value == v_clean or member.name.lower() == v_clean:
                    return member
        return v
