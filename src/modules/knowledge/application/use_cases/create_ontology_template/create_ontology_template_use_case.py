from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.application.use_cases.create_ontology_template.create_ontology_template_request import (  # noqa: E501
    CreateOntologyTemplateRequest,
)
from src.modules.knowledge.application.use_cases.create_ontology_template.create_ontology_template_response import (  # noqa: E501
    CreateOntologyTemplateResponse,
)
from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)
from src.modules.knowledge.domain.ontology.ontology_template import OntologyTemplate


class CreateOntologyTemplateUseCase:
    def __init__(self, repository: IOntologyRepository) -> None:
        self._repository = repository

    async def execute(
        self, request: CreateOntologyTemplateRequest
    ) -> Result[CreateOntologyTemplateResponse, DomainError]:
        # Verificar duplicidade por nome e versão
        existing = await self._repository.get_by_name_and_version(request.name, request.version)
        if existing:
            return Err(
                DomainError(
                    f"Já existe uma ontologia com nome '{request.name}' "
                    f"na versão {request.version}.",
                    "ONTOLOGY_ALREADY_EXISTS",
                    {"name": request.name, "version": request.version},
                )
            )

        template_res = OntologyTemplate.create(
            name=request.name,
            description=request.description,
            node_types=request.node_types,
            relationship_types=request.relationship_types,
            version=request.version,
        )
        if isinstance(template_res, Err):
            return Err(template_res.error)

        template = template_res.value
        await self._repository.save(template)

        return Ok(
            CreateOntologyTemplateResponse(
                id=template.id,
                name=template.name,
                version=template.version,
                description=template.description,
                node_types=template.node_types,
                relationship_types=template.relationship_types,
            )
        )
