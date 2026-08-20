from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.events.document_deleted_event import (
    DocumentDeletedEvent,
)
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage

from .delete_document_request import DeleteDocumentRequest
from .delete_document_response import DeleteDocumentResponse


class DeleteDocumentUseCase:
    """
    Caso de uso para exclusão atômica de um documento de uma Knowledge Base,
    removendo arquivos brutos e processados do Storage local,
    nós e arestas do FalkorDB, além da desnormalização no PostgreSQL.
    """

    def __init__(
        self,
        repository: IKnowledgeBaseRepository,
        object_storage: IObjectStorage,
        graph_store: IGraphStore,
        event_store: EventStore | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._repo = repository
        self._storage = object_storage
        self._graph_store = graph_store
        self._store = event_store
        self._bus = event_bus

    async def execute(
        self, request: DeleteDocumentRequest
    ) -> Result[DeleteDocumentResponse, DomainError]:
        if self._store:
            events = await self._store.get_events(request.kb_id)
            if events:
                kb = KnowledgeBaseAggregate(id=request.kb_id)
                kb.load_from_history(events)
            else:
                kb = await self._repo.get_by_id(request.kb_id)
        else:
            kb = await self._repo.get_by_id(request.kb_id)

        if not kb:
            return Err(
                DomainError(
                    f"Knowledge Base {request.kb_id} not found",
                    code="NOT_FOUND",
                )
            )

        if request.document_id not in kb.documents:
            return Err(
                DomainError(
                    f"Document {request.document_id} not found in Knowledge Base {request.kb_id}",
                    code="NOT_FOUND",
                )
            )

        storage_partition = kb.storage_partition or f"kb-{request.kb_id}"
        doc_id_str = str(request.document_id)

        # 1. Limpar arquivos do Storage Local correspondentes ao documento
        await self._storage.delete_prefix(f"{storage_partition}/raw/{doc_id_str}")
        await self._storage.delete_prefix(f"{storage_partition}/processed/{doc_id_str}")
        await self._storage.delete_prefix(f"{storage_partition}/checkpoints/{doc_id_str}")

        # 2. Limpar subgrafo do documento no FalkorDB
        await self._graph_store.delete_document_subgraph(request.kb_id, request.document_id)

        # 3. Atualizar aggregate e emitir evento
        kb.remove_document(request.document_id)
        if self._store:
            expected_version = kb.version - len(kb.uncommitted_events)
            events_to_publish = list(kb.uncommitted_events)
            kb.mark_events_as_committed()
            await self._store.append_events(
                aggregate_id=kb.id,
                aggregate_type="KnowledgeBaseAggregate",
                events=events_to_publish,
                expected_version=expected_version,
            )
        elif self._bus:
            await self._bus.publish(
                [
                    DocumentDeletedEvent(
                        aggregate_id=request.kb_id,
                        aggregate_type="KnowledgeBaseAggregate",
                        document_id=request.document_id,
                    )
                ]
            )

        # 4. Remover do Repositório Relacional (Postgres / In-Memory)
        await self._repo.delete_document(request.kb_id, request.document_id)

        return Ok(
            DeleteDocumentResponse(
                document_id=request.document_id,
                success=True,
                message=f"Document {request.document_id} successfully deleted.",
            )
        )
