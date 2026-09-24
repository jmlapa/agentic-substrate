import os
from uuid import uuid4

from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.application.use_cases.attach_and_store_document.attach_and_store_document_request import (  # noqa: E501
    AttachAndStoreDocumentRequest,
)
from src.modules.knowledge.application.use_cases.attach_and_store_document.attach_and_store_document_response import (  # noqa: E501
    AttachAndStoreDocumentResponse,
)
from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate
from src.modules.knowledge.domain.interfaces.i_document_repository import (
    IDocumentRepository,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.infrastructure.adapters.postgres_document_repository import (
    PostgresDocumentRepository,
)


class AttachAndStoreDocumentUseCase:
    """
    Caso de uso para anexo e armazenamento de documentos.
    Opera sobre DocumentAggregate como Agregado Raiz soberano (stream 'doc-{id}'),
    garantindo paralelismo irrestrito e zero colisões de concorrência com outros documentos.
    """

    def __init__(
        self,
        event_store: EventStore,
        repository: IKnowledgeBaseRepository,
        storage: IObjectStorage,
        document_repository: IDocumentRepository | None = None,
        document_repo: IDocumentRepository | None = None,
    ) -> None:
        self._store = event_store
        self._repo = repository
        self._storage = storage
        self._document_repo = (
            document_repository
            or document_repo
            or PostgresDocumentRepository(event_store=self._store)
        )

    async def execute(
        self, request: AttachAndStoreDocumentRequest
    ) -> Result[AttachAndStoreDocumentResponse, DomainError]:
        try:
            kb = await self._repo.get_by_id(request.kb_id)
            if kb is None:
                return Err(
                    DomainError(
                        f"Knowledge Base {request.kb_id} not found",
                        code="NOT_FOUND",
                    )
                )

            storage_partition = kb.storage_partition
            safe_file_name = os.path.basename(request.file_name) or "document"
            doc_id = uuid4()
            storage_path = f"{storage_partition}/raw/{doc_id}-{safe_file_name}"

            # 1. Armazena bytes brutos no Object Storage
            await self._storage.put_object(storage_path, request.file_content, request.content_type)

            # 2. Instancia o DocumentAggregate soberano
            doc = DocumentAggregate.create(
                document_id=doc_id,
                kb_id=request.kb_id,
                file_name=safe_file_name,
                content_type=request.content_type,
                storage_path=storage_path,
                enable_ocr=request.enable_ocr,
                ocr_instructions=request.ocr_instructions,
                metadata=request.source_metadata,
            )

            # 3. Transiciona para UPLOADED e persiste
            doc.mark_stored(storage_path=storage_path, byte_size=len(request.file_content))
            await self._document_repo.save(doc)

            return Ok(
                AttachAndStoreDocumentResponse(
                    document_id=doc_id,
                    storage_path=storage_path,
                    status="UPLOADED",
                )
            )
        except DomainError as err:
            return Err(err)
        except Exception as e:
            return Err(DomainError(str(e), code="INTERNAL_ERROR"))
