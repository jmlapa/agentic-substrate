from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from src.api_gateway.container import AppContainer
from src.api_gateway.dtos.create_knowledge_base_dto import (
    CreateKnowledgeBaseDTO,
)
from src.api_gateway.dtos.query_knowledge_dto import QueryKnowledgeDTO
from src.kernel.domain.result import Err
from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentRequest,
)
from src.modules.knowledge.application.use_cases.create_knowledge_base import (
    CreateKnowledgeBaseRequest,
    CreateKnowledgeBaseResponse,
)
from src.modules.knowledge.application.use_cases.list_knowledge_bases import (
    ListKnowledgeBasesRequest,
    ListKnowledgeBasesResponse,
)
from src.modules.knowledge.application.use_cases.query_knowledge import (
    QueryKnowledgeRequest,
    QueryKnowledgeResponse,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge"])


def get_container(request: Request) -> AppContainer:
    if hasattr(request.app.state, "container") and request.app.state.container:
        return request.app.state.container  # type: ignore[no-any-return]
    from src.api_gateway.main import container

    return container


@router.post(
    "/bases",
    response_model=CreateKnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_base(
    payload: CreateKnowledgeBaseDTO,
    container: AppContainer = Depends(get_container),
) -> CreateKnowledgeBaseResponse:
    res = await container.create_kb_use_case.execute(
        CreateKnowledgeBaseRequest(
            name=payload.name,
            description=payload.description,
            ontology_id=payload.ontology_id,
            ontology=payload.ontology,
        )
    )
    if isinstance(res, Err):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )
    return res.value


@router.get(
    "/bases",
    response_model=ListKnowledgeBasesResponse,
    status_code=status.HTTP_200_OK,
)
async def list_knowledge_bases(
    container: AppContainer = Depends(get_container),
) -> ListKnowledgeBasesResponse:
    res = await container.list_kbs_use_case.execute(ListKnowledgeBasesRequest())
    if isinstance(res, Err):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )
    return res.value


@router.post("/bases/{kb_id}/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_to_kb(
    kb_id: UUID,
    file: UploadFile = File(...),
    container: AppContainer = Depends(get_container),
) -> dict[str, str]:
    content = await file.read()
    file_name = file.filename or "uploaded_file.txt"
    content_type = file.content_type or "text/plain"

    res = await container.attach_doc_use_case.execute(
        AttachAndStoreDocumentRequest(
            kb_id=kb_id,
            file_name=file_name,
            content_type=content_type,
            file_content=content,
        )
    )
    if isinstance(res, Err):
        status_code = (
            status.HTTP_404_NOT_FOUND
            if res.error.code == "NOT_FOUND"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": res.error.code, "message": res.error.message},
        )

    return {
        "document_id": str(res.value.document_id),
        "storage_path": res.value.storage_path,
        "status": res.value.status,
    }


@router.post("/bases/{kb_id}/query", response_model=QueryKnowledgeResponse)
async def query_knowledge_base(
    kb_id: UUID,
    payload: QueryKnowledgeDTO,
    container: AppContainer = Depends(get_container),
) -> QueryKnowledgeResponse:
    res = await container.query_knowledge_use_case.execute(
        QueryKnowledgeRequest(
            kb_id=kb_id,
            query=payload.query,
            top_k=payload.top_k,
        )
    )
    if isinstance(res, Err):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )
    return res.value


@router.get("/bases/{kb_id}")
async def get_knowledge_base(
    kb_id: UUID,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    kb = await container.kb_repository.get_by_id(kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge Base not found",
        )
    return {
        "id": str(kb.id),
        "name": kb.name,
        "description": kb.description,
        "status": kb.status.value,
        "storage_partition": kb.storage_partition,
        "documents": [
            {
                "id": str(doc["id"]),
                "file_name": doc["file_name"],
                "status": (
                    doc["status"].value if hasattr(doc["status"], "value") else str(doc["status"])
                ),
            }
            for doc in kb.documents.values()
        ],
    }
