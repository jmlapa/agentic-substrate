from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api_gateway.container import AppContainer
from src.api_gateway.dtos.create_ontology_template_dto import (
    CreateOntologyTemplateDTO,
)
from src.kernel.domain.result import Err
from src.modules.knowledge.application.use_cases.create_ontology_template import (
    CreateOntologyTemplateRequest,
)
from src.modules.knowledge.application.use_cases.delete_ontology_template import (
    DeleteOntologyTemplateRequest,
    DeleteOntologyTemplateResponse,
)
from src.modules.knowledge.application.use_cases.get_ontology_template import (
    GetOntologyTemplateRequest,
)
from src.modules.knowledge.application.use_cases.list_ontology_templates import (
    ListOntologyTemplatesRequest,
)

ontology_router = APIRouter(prefix="/api/v1/ontologies", tags=["Ontologies"])


def get_container(request: Request) -> AppContainer:
    if hasattr(request.app.state, "container") and request.app.state.container:
        return request.app.state.container  # type: ignore[no-any-return]
    from src.api_gateway.main import container

    return container


@ontology_router.post("", status_code=status.HTTP_201_CREATED)
async def create_ontology_template(
    dto: CreateOntologyTemplateDTO,
    cont: AppContainer = Depends(get_container),
) -> dict[str, object]:
    req = CreateOntologyTemplateRequest(
        name=dto.name,
        description=dto.description,
        node_types=dto.node_types,
        relationship_types=dto.relationship_types,
        version=dto.version,
    )
    res = await cont.create_ontology_use_case.execute(req)
    if isinstance(res, Err):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )
    return res.value.model_dump()


@ontology_router.get("", status_code=status.HTTP_200_OK)
async def list_ontology_templates(
    cont: AppContainer = Depends(get_container),
) -> dict[str, object]:
    res = await cont.list_ontologies_use_case.execute(ListOntologyTemplatesRequest())
    if isinstance(res, Err):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )
    return res.value.model_dump()


@ontology_router.get("/{ontology_id}", status_code=status.HTTP_200_OK)
async def get_ontology_template_by_id(
    ontology_id: UUID,
    cont: AppContainer = Depends(get_container),
) -> dict[str, object]:
    res = await cont.get_ontology_use_case.execute(GetOntologyTemplateRequest(id=ontology_id))
    if isinstance(res, Err):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": res.error.code, "message": res.error.message},
        )
    return res.value.model_dump()


@ontology_router.delete("/{ontology_id}", response_model=DeleteOntologyTemplateResponse)
async def delete_ontology_template(
    ontology_id: UUID,
    cont: AppContainer = Depends(get_container),
) -> DeleteOntologyTemplateResponse:
    res = await cont.delete_ontology_use_case.execute(
        DeleteOntologyTemplateRequest(ontology_id=ontology_id)
    )
    if isinstance(res, Err):
        if res.error.code == "CONFLICT":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": res.error.code, "message": res.error.message},
            )
        if res.error.code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": res.error.code, "message": res.error.message},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )
    return res.value
