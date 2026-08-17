import hashlib
import math

from src.modules.knowledge.domain.interfaces.i_embedding_service import (
    IEmbeddingService,
)


class InMemoryEmbeddingService(IEmbeddingService):
    """
    Implementação em memória determinística de IEmbeddingService para testes locais.
    Gera vetores normalizados baseados em hash de conteúdo.
    """

    def __init__(self, dimension: int = 768) -> None:
        self._dimension = dimension

    def _generate_vector(self, text: str) -> list[float]:
        # Gera embedding determinístico a partir do hash do texto
        hasher = hashlib.sha256(text.encode("utf-8"))
        digest = hasher.digest()
        raw_values: list[float] = []

        for i in range(self._dimension):
            byte_val = digest[i % len(digest)]
            val = (float(byte_val) / 255.0) * 2.0 - 1.0
            raw_values.append(val)

        # Normalização para distância de cosseno unitária
        magnitude = math.sqrt(sum(x * x for x in raw_values))
        if magnitude == 0.0:
            return [0.0] * self._dimension

        return [x / magnitude for x in raw_values]

    async def embed_texts(
        self,
        texts: list[str],
        titles: list[str] | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for idx, text in enumerate(texts):
            title = titles[idx] if titles and idx < len(titles) else "none"
            formatted = f"title: {title} | text: {text}"
            embeddings.append(self._generate_vector(formatted))

        return embeddings

    async def embed_query(self, query: str) -> list[float]:
        formatted = f"task: search result | query: {query}"
        return self._generate_vector(formatted)
