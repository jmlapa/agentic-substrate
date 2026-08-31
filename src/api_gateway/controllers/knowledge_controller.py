from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

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
from src.modules.knowledge.application.use_cases.delete_document import (
    DeleteDocumentRequest,
    DeleteDocumentResponse,
)
from src.modules.knowledge.application.use_cases.delete_knowledge_base import (
    DeleteKnowledgeBaseRequest,
    DeleteKnowledgeBaseResponse,
)
from src.modules.knowledge.application.use_cases.get_document_content import (
    GetDocumentContentRequest,
    GetDocumentContentResponse,
)
from src.modules.knowledge.application.use_cases.list_knowledge_bases import (
    ListKnowledgeBasesRequest,
    ListKnowledgeBasesResponse,
)
from src.modules.knowledge.application.use_cases.query_knowledge import (
    QueryKnowledgeRequest,
    QueryKnowledgeResponse,
)
from src.modules.knowledge.application.use_cases.quick_search_notes import (
    QuickSearchNotesRequest,
    QuickSearchNotesResponse,
)
from src.modules.knowledge.application.use_cases.reprocess_document import (
    ReprocessDocumentRequest,
    ReprocessDocumentResponse,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.value_objects.knowledge_base_status import (
    KnowledgeBaseStatus,
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
    enable_ocr: bool = Form(default=False),
    ocr_instructions: str | None = Form(default=None),
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
            enable_ocr=enable_ocr,
            ocr_instructions=ocr_instructions,
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
            mode=payload.mode,
            max_tokens_budget=payload.max_tokens_budget,
            include_graph_triples=payload.include_graph_triples,
            source_types=payload.source_types,
            time_from=payload.time_from,
            time_to=payload.time_to,
            document_id=payload.document_id,
        )
    )
    if isinstance(res, Err):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": res.error.code, "message": res.error.message},
        )
    return res.value


@router.post(
    "/bases/{kb_id}/documents/{doc_id}/reprocess",
    response_model=ReprocessDocumentResponse,
)
async def reprocess_document(
    kb_id: UUID,
    doc_id: UUID,
    container: AppContainer = Depends(get_container),
) -> ReprocessDocumentResponse:
    res = await container.reprocess_document_use_case.execute(
        ReprocessDocumentRequest(
            kb_id=kb_id,
            document_id=doc_id,
        )
    )
    if isinstance(res, Err):
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


@router.get("/bases/{kb_id}")
async def get_knowledge_base(
    kb_id: UUID,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    kb = await container.kb_repository.get_by_id(kb_id)
    if not kb:
        # Fallback de resiliência caso a projeção ainda não tenha sido processada
        events = await container.event_store.get_events(kb_id)
        if events:
            aggregate = KnowledgeBaseAggregate(id=kb_id)
            aggregate.load_from_history(events)
            if aggregate.status != KnowledgeBaseStatus.ARCHIVED:
                kb = aggregate

    if not kb or kb.status == KnowledgeBaseStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge Base not found",
        )

    ontology_data: dict[str, Any] | None = None
    if kb.ontology:
        ontology_data = {
            "name": kb.ontology.name,
            "description": kb.ontology.description,
            "node_types": [nt.model_dump() for nt in kb.ontology.node_types],
            "relationship_types": [rt.model_dump() for rt in kb.ontology.relationship_types],
        }

    status_val = kb.status.value if isinstance(kb.status, KnowledgeBaseStatus) else str(kb.status)

    return {
        "id": str(kb.id),
        "name": kb.name,
        "description": kb.description,
        "status": status_val,
        "storage_partition": kb.storage_partition,
        "ontology": ontology_data,
        "documents": [
            {
                "id": str(doc["id"]),
                "file_name": doc.get("file_name", "document"),
                "status": (
                    doc["status"].value
                    if hasattr(doc.get("status"), "value")
                    else str(doc.get("status", "PENDING_UPLOAD"))
                ),
                "enable_ocr": bool(doc.get("enable_ocr", False)),
                "ocr_instructions": doc.get("ocr_instructions"),
                "total_parents": doc.get("total_parents"),
                "total_children": doc.get("total_children"),
                "indexed_nodes_count": doc.get("indexed_nodes_count", 0),
                "indexed_edges_count": doc.get("indexed_edges_count", 0),
                "progress_step": doc.get("progress_step"),
                "progress_current": doc.get("progress_current", 0),
                "progress_total": doc.get("progress_total", 0),
                "progress_percentage": doc.get("progress_percentage", 0),
                "progress_message": doc.get("progress_message"),
                "error": (
                    {
                        "step": doc["error"].get("step"),
                        "message": (
                            doc["error"].get("message") or doc["error"].get("error_message")
                        ),
                        "error_message": (
                            doc["error"].get("message") or doc["error"].get("error_message")
                        ),
                    }
                    if doc.get("error") and isinstance(doc["error"], dict)
                    else None
                ),
            }
            for doc in kb.documents.values()
        ],
    }


@router.delete("/bases/{kb_id}", response_model=DeleteKnowledgeBaseResponse)
async def delete_knowledge_base(
    kb_id: UUID,
    container: AppContainer = Depends(get_container),
) -> DeleteKnowledgeBaseResponse:
    res = await container.delete_kb_use_case.execute(DeleteKnowledgeBaseRequest(kb_id=kb_id))
    if isinstance(res, Err):
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


@router.delete("/bases/{kb_id}/documents/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    kb_id: UUID,
    doc_id: UUID,
    container: AppContainer = Depends(get_container),
) -> DeleteDocumentResponse:
    res = await container.delete_doc_use_case.execute(
        DeleteDocumentRequest(kb_id=kb_id, document_id=doc_id)
    )
    if isinstance(res, Err):
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


@router.get(
    "/bases/{kb_id}/documents/{doc_id}/content",
    response_model=GetDocumentContentResponse,
    status_code=status.HTTP_200_OK,
)
async def get_document_content(
    kb_id: UUID,
    doc_id: UUID,
    container: AppContainer = Depends(get_container),
) -> GetDocumentContentResponse:
    res = await container.get_document_content_use_case.execute(
        GetDocumentContentRequest(kb_id=kb_id, document_id=doc_id)
    )
    if isinstance(res, Err):
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


@router.get(
    "/bases/{kb_id}/quick-search",
    response_model=QuickSearchNotesResponse,
    status_code=status.HTTP_200_OK,
)
async def quick_search_notes(
    kb_id: UUID,
    q: str = Query(..., min_length=1, description="Termo de busca rápida"),
    limit: int = Query(default=10, ge=1, le=50, description="Limite de resultados"),
    container: AppContainer = Depends(get_container),
) -> QuickSearchNotesResponse:
    res = await container.quick_search_notes_use_case.execute(
        QuickSearchNotesRequest(kb_id=kb_id, query=q, limit=limit)
    )
    if isinstance(res, Err):
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
