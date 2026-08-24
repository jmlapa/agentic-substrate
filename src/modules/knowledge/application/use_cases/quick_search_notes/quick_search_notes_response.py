from pydantic import BaseModel, Field

from src.modules.knowledge.application.use_cases.quick_search_notes.quick_search_result_item_dto import (  # noqa: E501
    QuickSearchResultItemDTO,
)


class QuickSearchNotesResponse(BaseModel):
    query: str = Field(..., description="Termo pesquisado")
    results: list[QuickSearchResultItemDTO] = Field(
        default_factory=list, description="Lista de notas e seções correspondentes"
    )
