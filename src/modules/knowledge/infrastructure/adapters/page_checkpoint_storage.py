from uuid import UUID

from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage


class PageCheckpointStorage:
    """
    Gerenciador de cache/checkpoints atômicos de páginas OCR.
    Salva e recupera páginas transcritas em Markdown para garantir
    desperdício zero de tokens em caso de reinicialização ou falha.
    """

    def __init__(self, storage: IObjectStorage) -> None:
        self._storage = storage

    def _get_page_path(self, kb_partition: str, doc_id: UUID, page_num: int) -> str:
        return f"{kb_partition}/ocr_cache/{doc_id}/page_{page_num:04d}.md"

    async def has_page(self, kb_partition: str, doc_id: UUID, page_num: int) -> bool:
        path = self._get_page_path(kb_partition, doc_id, page_num)
        return await self._storage.exists(path)

    async def get_page(self, kb_partition: str, doc_id: UUID, page_num: int) -> str | None:
        path = self._get_page_path(kb_partition, doc_id, page_num)
        if not await self._storage.exists(path):
            return None
        raw_bytes = await self._storage.get_object(path)
        return raw_bytes.decode("utf-8")

    async def save_page(self, kb_partition: str, doc_id: UUID, page_num: int, content: str) -> None:
        path = self._get_page_path(kb_partition, doc_id, page_num)
        await self._storage.put_object(path, content.encode("utf-8"), "text/markdown")

    async def get_completed_pages(self, kb_partition: str, doc_id: UUID) -> set[int]:
        prefix = f"{kb_partition}/ocr_cache/{doc_id}/"
        keys = await self._storage.list_objects(prefix)
        completed: set[int] = set()
        for key in keys:
            if key.endswith(".md") and "page_" in key:
                name = key.split("/")[-1].replace("page_", "").replace(".md", "")
                try:
                    completed.add(int(name))
                except ValueError:
                    continue
        return completed
