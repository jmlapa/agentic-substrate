from typing import Protocol, runtime_checkable


@runtime_checkable
class IEmbeddingService(Protocol):
    async def embed_texts(
        self,
        texts: list[str],
        titles: list[str] | None = None,
    ) -> list[list[float]]: ...

    async def embed_query(self, query: str) -> list[float]: ...
