import pytest

from src.modules.knowledge.domain.interfaces.i_embedding_service import (
    IEmbeddingService,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_embedding_service import (
    InMemoryEmbeddingService,
)


@pytest.mark.asyncio
async def test_in_memory_embedding_service_implements_protocol() -> None:
    service = InMemoryEmbeddingService()
    assert isinstance(service, IEmbeddingService)


@pytest.mark.asyncio
async def test_in_memory_embedding_service_embed_texts() -> None:
    service = InMemoryEmbeddingService(dimension=768)
    texts = ["First text snippet", "Second text snippet"]
    titles = ["Doc 1", "Doc 2"]

    embeddings = await service.embed_texts(texts, titles)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 768
    assert len(embeddings[1]) == 768
    # Deterministic: same text yields same vector
    embeddings_again = await service.embed_texts(["First text snippet"], ["Doc 1"])
    assert embeddings[0] == embeddings_again[0]


@pytest.mark.asyncio
async def test_in_memory_embedding_service_embed_query() -> None:
    service = InMemoryEmbeddingService(dimension=768)
    query_vector = await service.embed_query("search for postgres vector store")
    assert len(query_vector) == 768
