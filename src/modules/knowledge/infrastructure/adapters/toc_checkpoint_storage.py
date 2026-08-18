import json
from uuid import UUID

from src.modules.knowledge.domain.entities.synthetic_document_toc import (
    SyntheticDocumentToc,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.domain.value_objects.hierarchical_toc_item import (
    HierarchicalTocItem,
)
from src.modules.knowledge.domain.value_objects.toc_batch_state import (
    TocBatchState,
)


class TocCheckpointStorage:
    """
    Gerenciador de cache/checkpoints atômicos para o Sumário Sintético (Synthetic ToC).
    Salva e recupera tanto lotes parciais (itens + estado de passagem) quanto o ToC final
    consolidado para garantir desperdício zero de tokens em caso de falha na saga.
    """

    def __init__(self, storage: IObjectStorage) -> None:
        self._storage = storage

    def _get_batch_path(self, kb_partition: str, doc_id: UUID, batch_index: int) -> str:
        return f"{kb_partition}/toc_cache/{doc_id}/batch_{batch_index:04d}.json"

    def _get_toc_path(self, kb_partition: str, doc_id: UUID) -> str:
        return f"{kb_partition}/toc_cache/{doc_id}/toc.json"

    async def has_batch(self, kb_partition: str, doc_id: UUID, batch_index: int) -> bool:
        path = self._get_batch_path(kb_partition, doc_id, batch_index)
        return await self._storage.exists(path)

    async def get_batch(
        self, kb_partition: str, doc_id: UUID, batch_index: int
    ) -> tuple[list[HierarchicalTocItem], TocBatchState] | None:
        path = self._get_batch_path(kb_partition, doc_id, batch_index)
        if not await self._storage.exists(path):
            return None
        raw_bytes = await self._storage.get_object(path)
        data = json.loads(raw_bytes.decode("utf-8"))
        items = [HierarchicalTocItem.model_validate(item) for item in data.get("items", [])]
        state = TocBatchState.model_validate(data.get("state", {}))
        return items, state

    async def save_batch(
        self,
        kb_partition: str,
        doc_id: UUID,
        batch_index: int,
        items: list[HierarchicalTocItem],
        state: TocBatchState,
    ) -> None:
        path = self._get_batch_path(kb_partition, doc_id, batch_index)
        payload = {
            "batch_index": batch_index,
            "items": [item.model_dump() for item in items],
            "state": state.model_dump(),
        }
        raw_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await self._storage.put_object(path, raw_bytes, "application/json")

    async def has_toc(self, kb_partition: str, doc_id: UUID) -> bool:
        path = self._get_toc_path(kb_partition, doc_id)
        return await self._storage.exists(path)

    async def get_toc(self, kb_partition: str, doc_id: UUID) -> SyntheticDocumentToc | None:
        path = self._get_toc_path(kb_partition, doc_id)
        if not await self._storage.exists(path):
            return None
        raw_bytes = await self._storage.get_object(path)
        data = json.loads(raw_bytes.decode("utf-8"))
        return SyntheticDocumentToc.model_validate(data)

    async def save_toc(self, kb_partition: str, doc_id: UUID, toc: SyntheticDocumentToc) -> None:
        path = self._get_toc_path(kb_partition, doc_id)
        raw_bytes = json.dumps(toc.model_dump(), ensure_ascii=False).encode("utf-8")
        await self._storage.put_object(path, raw_bytes, "application/json")
