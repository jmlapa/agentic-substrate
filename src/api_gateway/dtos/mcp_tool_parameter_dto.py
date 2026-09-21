from pydantic import BaseModel, Field


class McpToolParameterDTO(BaseModel):
    name: str = Field(..., description="Nome do parâmetro")
    type: str = Field(..., description="Tipo do parâmetro (ex: string, integer, boolean)")
    required: bool = Field(default=False, description="Indica se o parâmetro é obrigatório")
    description: str = Field(default="", description="Descrição do papel do parâmetro")
