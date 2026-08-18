from collections.abc import Callable, Coroutine
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.entities.synthetic_document_toc import (
    SyntheticDocumentToc,
)


@runtime_checkable
class ISyntheticTocExtractor(Protocol):
    """
    Protocolo de domínio para extração da árvore hierárquica (Synthetic ToC)
    de documentos multimodais de forma assíncrona.
    """

    async def extract_toc(
        self,
        raw_bytes: bytes,
        batch_size: int = 25,
        progress_callback: (Callable[[int, int, str], Coroutine[Any, Any, None]] | None) = None,
        doc_id: UUID | None = None,
        kb_partition: str | None = None,
    ) -> SyntheticDocumentToc: ...
