import logging
from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)

from src.api_gateway.container import AppContainer
from src.api_gateway.dtos.create_data_source_dto import CreateDataSourceDTO
from src.api_gateway.dtos.data_source_response_dto import DataSourceResponseDTO
from src.api_gateway.dtos.data_source_run_response_dto import (
    DataSourceRunResponseDTO,
)
from src.api_gateway.dtos.sync_data_source_response_dto import (
    SyncDataSourceResponseDTO,
)
from src.kernel.domain.result import Err
from src.modules.knowledge.application.use_cases.create_data_source import (
    CreateDataSourceRequest,
)
from src.modules.knowledge.application.use_cases.delete_data_source import (
    DeleteDataSourceRequest,
)
from src.modules.knowledge.application.use_cases.list_data_source_runs import (
    ListDataSourceRunsRequest,
)
from src.modules.knowledge.application.use_cases.list_data_sources import (
    ListDataSourcesRequest,
)
from src.modules.knowledge.application.use_cases.sync_data_source import (
    SyncDataSourceRequest,
)

_logger = logging.getLogger("agentic_substrate.api.data_source_controller")

router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["Data Sources"])
data_source_router = router


def get_container(request: Request) -> AppContainer:
    if hasattr(request.app.state, "container") and request.app.state.container:
        return request.app.state.container  # type: ignore[no-any-return]
    from src.api_gateway.main import container

    return container


@router.post(
    "/{kb_id}/data-sources",
    response_model=DataSourceResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_data_source(
    kb_id: UUID,
    payload: CreateDataSourceDTO,
    container: AppContainer = Depends(get_container),
) -> DataSourceResponseDTO:
    _logger.info(
        f"[DataSourceController] POST create_data_source kb_id={kb_id}, "
        f"name='{payload.name}', type='{payload.data_source_type.value}'"
    )
    if container.create_data_source_use_case is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CreateDataSourceUseCase não configurado no container",
        )

    res = await container.create_data_source_use_case.execute(
        CreateDataSourceRequest(
            kb_id=kb_id,
            name=payload.name,
            data_source_type=payload.data_source_type,
            config=payload.config,
            sync_interval_minutes=payload.sync_interval_minutes,
        )
    )
    if isinstance(res, Err):
        _logger.warning(
            f"[DataSourceController] Erro ao criar DataSource para KB {kb_id}: "
            f"{res.error.code} - {res.error.message}"
        )
        if res.error.code == "KNOWLEDGE_BASE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": res.error.code, "message": res.error.message},
            )
        if res.error.code == "DATA_SOURCE_ALREADY_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": res.error.code, "message": res.error.message},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )

    return DataSourceResponseDTO.from_response(res.value)


@router.get(
    "/{kb_id}/data-sources",
    response_model=list[DataSourceResponseDTO],
    status_code=status.HTTP_200_OK,
)
async def list_data_sources(
    kb_id: UUID,
    container: AppContainer = Depends(get_container),
) -> list[DataSourceResponseDTO]:
    _logger.info(f"[DataSourceController] GET list_data_sources kb_id={kb_id}")
    if container.list_data_sources_use_case is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ListDataSourcesUseCase não configurado no container",
        )

    res = await container.list_data_sources_use_case.execute(ListDataSourcesRequest(kb_id=kb_id))
    if isinstance(res, Err):
        _logger.warning(
            f"[DataSourceController] Erro ao listar DataSources da KB {kb_id}: "
            f"{res.error.code} - {res.error.message}"
        )
        if res.error.code == "KNOWLEDGE_BASE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": res.error.code, "message": res.error.message},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )

    return [DataSourceResponseDTO.from_item_dto(item) for item in res.value.data_sources]


@router.delete(
    "/{kb_id}/data-sources/{data_source_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_data_source(
    kb_id: UUID,
    data_source_id: UUID,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    _logger.info(
        f"[DataSourceController] DELETE delete_data_source kb_id={kb_id}, "
        f"data_source_id={data_source_id}"
    )
    if container.delete_data_source_use_case is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DeleteDataSourceUseCase não configurado no container",
        )

    res = await container.delete_data_source_use_case.execute(
        DeleteDataSourceRequest(data_source_id=data_source_id, kb_id=kb_id)
    )
    if isinstance(res, Err):
        _logger.warning(
            f"[DataSourceController] Erro ao deletar DataSource {data_source_id}: "
            f"{res.error.code} - {res.error.message}"
        )
        if res.error.code == "DATA_SOURCE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": res.error.code, "message": res.error.message},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )

    return {"data_source_id": str(res.value.data_source_id), "success": res.value.success}


@router.post(
    "/{kb_id}/data-sources/{data_source_id}/sync",
    response_model=SyncDataSourceResponseDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_data_source(
    kb_id: UUID,
    data_source_id: UUID,
    container: AppContainer = Depends(get_container),
) -> SyncDataSourceResponseDTO:
    _logger.info(
        f"[DataSourceController] POST sync_data_source kb_id={kb_id}, "
        f"data_source_id={data_source_id}"
    )
    if container.sync_data_source_use_case is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SyncDataSourceUseCase não configurado no container",
        )

    res = await container.sync_data_source_use_case.execute(
        SyncDataSourceRequest(data_source_id=data_source_id, kb_id=kb_id)
    )
    if isinstance(res, Err):
        _logger.warning(
            f"[DataSourceController] Erro ao sincronizar DataSource {data_source_id}: "
            f"{res.error.code} - {res.error.message}"
        )
        if res.error.code == "DATA_SOURCE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": res.error.code, "message": res.error.message},
            )
        if res.error.code == "DATA_SOURCE_ALREADY_SYNCING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": res.error.code, "message": res.error.message},
            )
        if res.error.code == "DATA_SOURCE_DISABLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": res.error.code, "message": res.error.message},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )

    return SyncDataSourceResponseDTO(
        data_source_id=res.value.data_source_id,
        sync_run_id=res.value.sync_run_id,
        total_items_discovered=res.value.total_items_discovered,
        status=res.value.status,
        message="Sincronização iniciada com sucesso. Ingestão em andamento.",
    )


@router.get(
    "/{kb_id}/data-sources/{data_source_id}/runs",
    response_model=list[DataSourceRunResponseDTO],
    status_code=status.HTTP_200_OK,
)
async def list_data_source_runs(
    kb_id: UUID,
    data_source_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    container: AppContainer = Depends(get_container),
) -> list[DataSourceRunResponseDTO]:
    _logger.info(
        f"[DataSourceController] GET list_data_source_runs kb_id={kb_id}, "
        f"data_source_id={data_source_id}, limit={limit}"
    )
    if container.list_data_source_runs_use_case is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ListDataSourceRunsUseCase não configurado no container",
        )

    res = await container.list_data_source_runs_use_case.execute(
        ListDataSourceRunsRequest(data_source_id=data_source_id, limit=limit, kb_id=kb_id)
    )
    if isinstance(res, Err):
        _logger.warning(
            f"[DataSourceController] Erro ao listar runs do DataSource {data_source_id}: "
            f"{res.error.code} - {res.error.message}"
        )
        if res.error.code == "DATA_SOURCE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": res.error.code, "message": res.error.message},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )

    return [DataSourceRunResponseDTO.from_item_dto(run) for run in res.value.runs]
