import json
from uuid import UUID

from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph


class ParentGraphCheckpointStorage:
    """
    Gerenciador de cache/checkpoints atômicos de grafos ontológicos extraídos por Parent Chunk.
    Salva e recupera nós e arestas serializados para garantir
    desperdício zero de tokens em caso de retomada ou falha.
    """

    def __init__(self, storage: IObjectStorage) -> None:
        self._storage = storage

    def _get_parent_path(self, kb_partition: str, doc_id: UUID, parent_id: str) -> str:
        # Sanitizar parent_id para nome de arquivo seguro
        safe_id = parent_id.replace("/", "_").replace(":", "_")
        return f"{kb_partition}/graph_cache/{doc_id}/parent_{safe_id}.json"

    async def has_parent(self, kb_partition: str, doc_id: UUID, parent_id: str) -> bool:
        path = self._get_parent_path(kb_partition, doc_id, parent_id)
        return await self._storage.exists(path)

    async def get_parent(
        self, kb_partition: str, doc_id: UUID, parent_id: str
    ) -> ExtractedGraph | None:
        path = self._get_parent_path(kb_partition, doc_id, parent_id)
        if not await self._storage.exists(path):
            return None
        raw_bytes = await self._storage.get_object(path)
        data = json.loads(raw_bytes.decode("utf-8"))
        return ExtractedGraph.model_validate(data)

    async def save_parent(
        self,
        kb_partition: str,
        doc_id: UUID,
        parent_id: str,
        graph: ExtractedGraph,
    ) -> None:
        path = self._get_parent_path(kb_partition, doc_id, parent_id)
        data_json = json.dumps(graph.model_dump(), ensure_ascii=False)
        await self._storage.put_object(path, data_json.encode("utf-8"), "application/json")
