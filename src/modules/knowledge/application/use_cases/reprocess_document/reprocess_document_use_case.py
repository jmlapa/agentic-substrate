import asyncpg

from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate
from src.modules.knowledge.domain.interfaces.i_document_repository import (
    IDocumentRepository,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.infrastructure.adapters.postgres_document_repository import (
    PostgresDocumentRepository,
)

from .reprocess_document_request import ReprocessDocumentRequest
from .reprocess_document_response import ReprocessDocumentResponse


class ReprocessDocumentUseCase:
    """
    Caso de uso para retomar ou reprocessar um documento que tenha falhado
    ou sido interrompido, reaproveitando checkpoints atômicos em disco com $0 de custo de tokens.
    Opera sobre o Aggregate Root soberano DocumentAggregate com complexidade O(1).
    """

    def __init__(
        self,
        event_store: EventStore,
        repository: IKnowledgeBaseRepository,
        event_bus: EventBus,
        document_repo: IDocumentRepository | None = None,
        pool: asyncpg.Pool | None = None,
    ) -> None:
        self._store = event_store
        self._repo = repository
        self._bus = event_bus
        self._pool = pool
        self._doc_repo = document_repo or PostgresDocumentRepository(
            event_store=self._store, pool=self._pool
        )

    async def execute(
        self, request: ReprocessDocumentRequest
    ) -> Result[ReprocessDocumentResponse, DomainError]:
        kb = await self._repo.get_by_id(request.kb_id)
        if kb is None:
            return Err(
                DomainError(
                    f"Knowledge Base {request.kb_id} not found",
                    code="NOT_FOUND",
                )
            )

        doc = await self._doc_repo.get_by_id(request.document_id)
        if doc is None and self._pool is not None:
            async with self._pool.acquire() as conn:
                doc_row = await conn.fetchrow(
                    """
                    SELECT file_name, storage_path, byte_size
                    FROM attached_documents
                    WHERE id = $1;
                    """,
                    request.document_id,
                )
            if doc_row is not None:
                file_name = doc_row["file_name"]
                storage_path = doc_row["storage_path"]
                byte_size = doc_row.get("byte_size") or 0
                content_type = (
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    if file_name.endswith(".docx")
                    else (
                        "application/pdf"
                        if file_name.endswith(".pdf")
                        else "application/octet-stream"
                    )
                )
                doc = DocumentAggregate.create(
                    document_id=request.document_id,
                    kb_id=request.kb_id,
                    file_name=file_name,
                    content_type=content_type,
                    storage_path=storage_path,
                )
                doc.mark_stored(storage_path, byte_size)
                await self._doc_repo.save(doc)

        if doc is None:
            return Err(
                DomainError(
                    f"Document {request.document_id} not found",
                    code="NOT_FOUND",
                )
            )

        if doc.status == DocumentStatus.DELETED:
            return Err(
                DomainError(
                    f"Cannot reprocess deleted document {request.document_id}",
                    code="INVALID_STATE",
                )
            )

        doc.mark_stored(doc.storage_path, doc.byte_size)
        await self._doc_repo.save(doc)

        return Ok(
            ReprocessDocumentResponse(
                document_id=request.document_id,
                status="UPLOADED",
                message="Saga reiniciada com sucesso a partir dos checkpoints existentes.",
            )
        )
