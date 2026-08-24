from src.kernel.application.event_bus import EventBus
from src.kernel.application.event_store import EventStore
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.events.knowledge_base_deleted_event import (
    KnowledgeBaseDeletedEvent,
)
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage

from .delete_knowledge_base_request import DeleteKnowledgeBaseRequest
from .delete_knowledge_base_response import DeleteKnowledgeBaseResponse


class DeleteKnowledgeBaseUseCase:
    """
    Caso de uso para exclusão atômica e em cascata de uma Knowledge Base,
    removendo artefatos do Storage local, grafos e índices vetoriais no FalkorDB,
    além dos registros e eventos de domínio no PostgreSQL.
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
        self, request: DeleteKnowledgeBaseRequest
    ) -> Result[DeleteKnowledgeBaseResponse, DomainError]:
        kb: KnowledgeBaseAggregate | None = None
        if self._store:
            events = await self._store.get_events(request.kb_id)
            if events:
                aggregate = KnowledgeBaseAggregate(id=request.kb_id)
                aggregate.load_from_history(events)
                kb = aggregate
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

        storage_partition = kb.storage_partition or f"kb-{request.kb_id}"

        # 1. Limpar arquivos do Storage Local
        await self._storage.delete_prefix(storage_partition)

        # 2. Limpar grafo completo no FalkorDB
        await self._graph_store.delete_graph(request.kb_id)

        # 3. Disparar evento de exclusão no aggregate e event store
        kb.delete()
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
                    KnowledgeBaseDeletedEvent(
                        aggregate_id=request.kb_id,
                        aggregate_type="KnowledgeBaseAggregate",
                    )
                ]
            )

        # 4. Remover do Repositório Relacional (Postgres / In-Memory)
        await self._repo.delete_by_id(request.kb_id)

        return Ok(
            DeleteKnowledgeBaseResponse(
                kb_id=request.kb_id,
                success=True,
                message=f"Knowledge Base {request.kb_id} successfully deleted.",
            )
        )
