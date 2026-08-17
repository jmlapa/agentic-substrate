from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Ok, Result
from src.modules.knowledge.application.use_cases.list_knowledge_bases.knowledge_base_summary_dto import (  # noqa: E501
    KnowledgeBaseSummaryDTO,
)
from src.modules.knowledge.application.use_cases.list_knowledge_bases.list_knowledge_bases_request import (  # noqa: E501
    ListKnowledgeBasesRequest,
)
from src.modules.knowledge.application.use_cases.list_knowledge_bases.list_knowledge_bases_response import (  # noqa: E501
    ListKnowledgeBasesResponse,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)


class ListKnowledgeBasesUseCase:
    def __init__(self, repository: IKnowledgeBaseRepository) -> None:
        self._repository = repository

    async def execute(
        self, request: ListKnowledgeBasesRequest
    ) -> Result[ListKnowledgeBasesResponse, DomainError]:
        kbs = await self._repository.list_all()

        summaries = [
            KnowledgeBaseSummaryDTO(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                status=kb.status.value,
                storage_partition=kb.storage_partition,
                documents_count=len(kb.documents),
            )
            for kb in kbs
        ]

        return Ok(ListKnowledgeBasesResponse(knowledge_bases=summaries))
