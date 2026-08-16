from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
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
from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema


class CreateKnowledgeBaseUseCase:
    def __init__(
        self,
        event_store: EventStore,
        repository: IKnowledgeBaseRepository,
        ontology_repository: IOntologyRepository | None = None,
    ) -> None:
        self._store = event_store
        self._repo = repository
        self._ontology_repo = ontology_repository

    async def execute(
        self, request: CreateKnowledgeBaseRequest
    ) -> Result[CreateKnowledgeBaseResponse, DomainError]:
        ontology_to_use: OntologySchema | None = None

        if request.ontology_id is not None:
            if self._ontology_repo is None:
                return Err(
                    DomainError(
                        "Repositório de ontologia não configurado.",
                        "ONTOLOGY_REPOSITORY_NOT_CONFIGURED",
                    )
                )
            template = await self._ontology_repo.get_by_id(request.ontology_id)
            if template is None:
                return Err(
                    DomainError(
                        f"Template de ontologia com id '{request.ontology_id}' não foi encontrado.",
                        "ONTOLOGY_TEMPLATE_NOT_FOUND",
                    )
                )
            ontology_to_use = OntologySchema(
                name=template.name,
                description=template.description,
                node_types=template.node_types,
                relationship_types=template.relationship_types,
            )
        elif request.ontology is not None:
            ontology_to_use = request.ontology
        else:
            return Err(
                DomainError(
                    "É obrigatório fornecer ou 'ontology_id' ou o objeto 'ontology'.",
                    "MISSING_ONTOLOGY_DEFINITION",
                )
            )

        kb = KnowledgeBaseAggregate.create(
            name=request.name,
            description=request.description,
            ontology=ontology_to_use,
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
