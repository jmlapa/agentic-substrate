from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Ok, Result
from src.modules.knowledge.application.use_cases.create_knowledge_base.create_knowledge_base_request import (  # noqa: E501
    CreateKnowledgeBaseRequest,
)
from src.modules.knowledge.application.use_cases.create_knowledge_base.create_knowledge_base_response import (  # noqa: E501
    CreateKnowledgeBaseResponse,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)


class CreateKnowledgeBaseUseCase:
    def __init__(
        self,
        event_store: EventStore,
        repository: IKnowledgeBaseRepository,
    ) -> None:
        self._store = event_store
        self._repo = repository

    async def execute(
        self, request: CreateKnowledgeBaseRequest
    ) -> Result[CreateKnowledgeBaseResponse, DomainError]:
        kb = KnowledgeBaseAggregate.create(
            name=request.name,
            description=request.description,
            ontology=request.ontology,
        )
        await self._store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=kb.uncommitted_events,
            expected_version=0,
        )
        kb.mark_events_as_committed()
        await self._repo.save(kb)

        return Ok(
            CreateKnowledgeBaseResponse(
                id=kb.id,
                name=kb.name,
                storage_partition=kb.storage_partition,
                status=kb.status.value,
            )
        )
