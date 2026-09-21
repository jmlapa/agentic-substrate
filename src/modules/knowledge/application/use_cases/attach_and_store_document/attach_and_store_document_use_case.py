from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.application.use_cases.attach_and_store_document.attach_and_store_document_request import (  # noqa: E501
    AttachAndStoreDocumentRequest,
)
from src.modules.knowledge.application.use_cases.attach_and_store_document.attach_and_store_document_response import (  # noqa: E501
    AttachAndStoreDocumentResponse,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage


class AttachAndStoreDocumentUseCase:
    def __init__(
        self,
        event_store: EventStore,
        repository: IKnowledgeBaseRepository,
        storage: IObjectStorage,
    ) -> None:
        self._store = event_store
        self._repo = repository
        self._storage = storage

    async def execute(
        self, request: AttachAndStoreDocumentRequest
    ) -> Result[AttachAndStoreDocumentResponse, DomainError]:
        events = await self._store.get_events(request.kb_id)
        if not events:
            return Err(
                DomainError(
                    f"Knowledge Base {request.kb_id} not found",
                    code="NOT_FOUND",
                )
            )

        kb = KnowledgeBaseAggregate(id=request.kb_id)
        kb.load_from_history(events)

        doc_id = kb.attach_document(
            file_name=request.file_name,
            content_type=request.content_type,
            enable_ocr=request.enable_ocr,
            ocr_instructions=request.ocr_instructions,
            metadata=request.source_metadata,
        )
        doc_info = kb.documents[doc_id]
        storage_path = doc_info["storage_path"]

        await self._storage.put_object(storage_path, request.file_content, request.content_type)
        kb.mark_document_stored(doc_id, storage_path, len(request.file_content))

        expected_version = kb.version - len(kb.uncommitted_events)
        events_to_append = list(kb.uncommitted_events)
        kb.mark_events_as_committed()
        await self._repo.save(kb)
        await self._store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=events_to_append,
            expected_version=expected_version,
        )

        return Ok(
            AttachAndStoreDocumentResponse(
                document_id=doc_id,
                storage_path=storage_path,
                status="UPLOADED",
            )
        )
