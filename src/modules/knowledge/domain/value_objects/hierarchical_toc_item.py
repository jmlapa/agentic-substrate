from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HierarchicalTocItem(BaseModel):
    """
    Value Object imutável representando um item estrutural descoberto no ToC.
    Classifica tipo ontológico, nível markdown, numeração/título e parentesco hierárquico.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["document_title", "section", "subsection", "sub_subsection"] = Field(
        description="Classificação estrutural do nó"
    )
    markdown_level: Literal["#", "##", "###", "####"] = Field(
        description="Nível estrito de cabeçalho Markdown (# a ####)"
    )
    title: str = Field(description="Título ou cabeçalho completo com numeração original")
    page: int = Field(ge=1, description="Número da página (1-indexed) onde o elemento se inicia")
    parent_section: str | None = Field(
        default=None,
        description=(
            "Título da seção pai imediata para subseções ou None para seções de nível superior"
        ),
    )
