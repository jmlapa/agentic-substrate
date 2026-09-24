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
from src.modules.knowledge.domain.interfaces.i_document_repository import (
    IDocumentRepository,
)
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.infrastructure.adapters.postgres_document_repository import (
    PostgresDocumentRepository,
)

from .delete_document_request import DeleteDocumentRequest
from .delete_document_response import DeleteDocumentResponse


class DeleteDocumentUseCase:
    """
    Caso de uso para exclusão atômica de um documento de uma Knowledge Base,
    removendo arquivos brutos e processados do Storage local,
    nós e arestas do FalkorDB, além da desnormalização no PostgreSQL.
    Opera sobre DocumentAggregate como Agregado Raiz soberano.
    """

    def __init__(
        self,
        repository: IKnowledgeBaseRepository,
        object_storage: IObjectStorage,
        graph_store: IGraphStore,
        event_store: EventStore | None = None,
        event_bus: EventBus | None = None,
        document_repo: IDocumentRepository | None = None,
    ) -> None:
        self._repo = repository
        self._storage = object_storage
        self._graph_store = graph_store
        self._store = event_store
        self._bus = event_bus
        self._doc_repo = document_repo or (
            PostgresDocumentRepository(event_store=self._store) if self._store else None
        )

    async def execute(
        self, request: DeleteDocumentRequest
    ) -> Result[DeleteDocumentResponse, DomainError]:
        kb: KnowledgeBaseAggregate | None = await self._repo.get_by_id(request.kb_id)
        if not kb:
            return Err(
                DomainError(
                    f"Knowledge Base {request.kb_id} not found",
                    code="NOT_FOUND",
                )
            )

        doc = None
        if self._doc_repo is not None:
            doc = await self._doc_repo.get_by_id(request.document_id)

        if not doc and request.document_id not in kb.documents:
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

        # 3. Excluir aggregate soberano e emitir evento de domínio
        if doc is not None and self._doc_repo is not None:
            doc.delete()
            await self._doc_repo.save(doc)
        elif self._bus is not None:
            await self._bus.publish(
                [
                    DocumentDeletedEvent(
                        aggregate_id=request.document_id,
                        aggregate_type="DocumentAggregate",
                        document_id=request.document_id,
                        kb_id=request.kb_id,
                    )
                ]
            )

        # 4. Remover do Repositório Relacional / Projeção em Memória
        await self._repo.delete_document(request.kb_id, request.document_id)

        return Ok(
            DeleteDocumentResponse(
                document_id=request.document_id,
                success=True,
                message=f"Document {request.document_id} successfully deleted.",
            )
        )
