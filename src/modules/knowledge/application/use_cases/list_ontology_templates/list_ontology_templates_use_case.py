from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Ok, Result
from src.modules.knowledge.application.use_cases.get_ontology_template.get_ontology_template_response import (  # noqa: E501
    GetOntologyTemplateResponse,
)
from src.modules.knowledge.application.use_cases.list_ontology_templates.list_ontology_templates_request import (  # noqa: E501
    ListOntologyTemplatesRequest,
)
from src.modules.knowledge.application.use_cases.list_ontology_templates.list_ontology_templates_response import (  # noqa: E501
    ListOntologyTemplatesResponse,
)
from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)


class ListOntologyTemplatesUseCase:
    def __init__(self, repository: IOntologyRepository) -> None:
        self._repository = repository

    async def execute(
        self, request: ListOntologyTemplatesRequest
    ) -> Result[ListOntologyTemplatesResponse, DomainError]:
        templates = await self._repository.list_all()

        mapped = [
            GetOntologyTemplateResponse(
                id=t.id,
                name=t.name,
                version=t.version,
                description=t.description,
                node_types=t.node_types,
                relationship_types=t.relationship_types,
            )
            for t in templates
        ]

        return Ok(ListOntologyTemplatesResponse(templates=mapped))
