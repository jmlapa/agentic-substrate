from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)

from .reprocess_document_request import ReprocessDocumentRequest
from .reprocess_document_response import ReprocessDocumentResponse


class ReprocessDocumentUseCase:
    """
    Caso de uso para retomar ou reprocessar um documento que tenha falhado
    ou sido interrompido, reaproveitando checkpoints atômicos em disco com $0 de custo de tokens.
    """

    def __init__(
        self,
        event_store: EventStore,
        repository: IKnowledgeBaseRepository,
        event_bus: EventBus,
    ) -> None:
        self._store = event_store
        self._repo = repository
        self._bus = event_bus

    async def execute(
        self, request: ReprocessDocumentRequest
    ) -> Result[ReprocessDocumentResponse, DomainError]:
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

        if request.document_id not in kb.documents:
            return Err(
                DomainError(
                    f"Document {request.document_id} not found in Knowledge Base {request.kb_id}",
                    code="NOT_FOUND",
                )
            )

        doc_info = kb.documents[request.document_id]
        storage_path = doc_info.get("storage_path", "")
        byte_size = doc_info.get("byte_size", 0)

        # Reseta o documento para status UPLOADED e re-dispara o DocumentStoredEvent
        kb.mark_document_stored(request.document_id, storage_path, byte_size)

        expected_version = kb.version - len(kb.uncommitted_events)
        events_to_publish = list(kb.uncommitted_events)
        kb.mark_events_as_committed()
        await self._repo.save(kb)
        await self._store.append_events(
            aggregate_id=kb.id,
            aggregate_type="KnowledgeBaseAggregate",
            events=events_to_publish,
            expected_version=expected_version,
        )

        return Ok(
            ReprocessDocumentResponse(
                document_id=request.document_id,
                status="UPLOADED",
                message="Saga reiniciada com sucesso a partir dos checkpoints existentes.",
            )
        )
