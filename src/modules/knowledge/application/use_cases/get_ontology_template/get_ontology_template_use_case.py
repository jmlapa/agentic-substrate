from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.application.use_cases.get_ontology_template.get_ontology_template_request import (  # noqa: E501
    GetOntologyTemplateRequest,
)
from src.modules.knowledge.application.use_cases.get_ontology_template.get_ontology_template_response import (  # noqa: E501
    GetOntologyTemplateResponse,
)
from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)
from src.modules.knowledge.domain.ontology.ontology_template import OntologyTemplate


class GetOntologyTemplateUseCase:
    def __init__(self, repository: IOntologyRepository) -> None:
        self._repository = repository

    async def execute(
        self, request: GetOntologyTemplateRequest
    ) -> Result[GetOntologyTemplateResponse, DomainError]:
        template: OntologyTemplate | None = None

        if request.id is not None:
            template = await self._repository.get_by_id(request.id)
        elif request.name is not None and request.version is not None:
            template = await self._repository.get_by_name_and_version(request.name, request.version)
        else:
            return Err(
                DomainError(
                    "É necessário informar ou o 'id' ou o par 'name' e 'version'.",
                    "INVALID_GET_ONTOLOGY_REQUEST",
                )
            )

        if template is None:
            return Err(
                DomainError(
                    "Ontologia não encontrada.",
                    "ONTOLOGY_NOT_FOUND",
                )
            )

        return Ok(
            GetOntologyTemplateResponse(
                id=template.id,
                name=template.name,
                version=template.version,
                description=template.description,
                node_types=template.node_types,
                relationship_types=template.relationship_types,
            )
        )
