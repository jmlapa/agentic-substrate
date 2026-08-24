from pydantic import BaseModel, Field


class DocumentTocItemDTO(BaseModel):
    level: int = Field(..., description="Nível do cabeçalho (1 a 6)")
    title: str = Field(..., description="Texto do cabeçalho")
    anchor: str = Field(..., description="Slug âncora para navegação")
