from pydantic import BaseModel, Field

from src.modules.knowledge.application.use_cases.list_knowledge_bases.knowledge_base_summary_dto import (  # noqa: E501
    KnowledgeBaseSummaryDTO,
)


class ListKnowledgeBasesResponse(BaseModel):
    knowledge_bases: list[KnowledgeBaseSummaryDTO] = Field(
        default_factory=list, description="Lista de Knowledge Bases"
    )
