from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)

from .delete_ontology_template_request import DeleteOntologyTemplateRequest
from .delete_ontology_template_response import DeleteOntologyTemplateResponse


class DeleteOntologyTemplateUseCase:
    """
    Caso de uso para exclusão de templates de ontologia.
    Garante integridade referencial impedindo a exclusão caso a ontologia
    esteja vinculada a uma ou mais Knowledge Bases ativas.
    """

    def __init__(self, repository: IOntologyRepository) -> None:
        self._repo = repository

    async def execute(
        self, request: DeleteOntologyTemplateRequest
    ) -> Result[DeleteOntologyTemplateResponse, DomainError]:
        template = await self._repo.get_by_id(request.ontology_id)
        if not template:
            return Err(
                DomainError(
                    f"Ontology template {request.ontology_id} not found",
                    code="NOT_FOUND",
                )
            )

        usages = await self._repo.count_usages(request.ontology_id)
        if usages > 0:
            return Err(
                DomainError(
                    f"Cannot delete ontology template '{template.name}' ({request.ontology_id}) "
                    f"because it is currently linked to {usages} Knowledge Base(s).",
                    code="CONFLICT",
                )
            )

        await self._repo.delete_by_id(request.ontology_id)

        return Ok(
            DeleteOntologyTemplateResponse(
                ontology_id=request.ontology_id,
                success=True,
                message=f"Ontology template '{template.name}' successfully deleted.",
            )
        )
