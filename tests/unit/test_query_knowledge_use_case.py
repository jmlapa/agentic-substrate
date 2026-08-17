from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.kernel.domain.result import Ok
from src.modules.knowledge.application.use_cases.query_knowledge.query_knowledge_request import (
    QueryKnowledgeRequest,
)
from src.modules.knowledge.application.use_cases.query_knowledge.query_knowledge_response import (
    QueryKnowledgeResponse,
)
from src.modules.knowledge.application.use_cases.query_knowledge.query_knowledge_use_case import (
    QueryKnowledgeUseCase,
)
from src.modules.knowledge.domain.interfaces.i_embedding_service import (
    IEmbeddingService,
)
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.value_objects.hybrid_search_result import (
    HybridSearchResult,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_rag_synthesizer import (
    InMemoryRagSynthesizer,
)


@pytest.mark.asyncio
async def test_query_knowledge_use_case_success() -> None:
    mock_graph_store = AsyncMock(spec=IGraphStore)
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)
    synthesizer = InMemoryRagSynthesizer()

    kb_id = uuid4()
    mock_embedding_service.embed_texts.return_value = [[0.1, 0.2, 0.3]]

    expected_results = [
        HybridSearchResult(
            parent_chunk_id="parent-1",
            header_path="# Section 1",
            parent_content="Relevant content about security.",
            relevance_score=0.94,
            related_entities=[{"type": "Concept", "properties": {"name": "Security"}}],
        )
    ]
    mock_graph_store.query_hybrid.return_value = expected_results

    use_case = QueryKnowledgeUseCase(
        graph_store=mock_graph_store,
        embedding_service=mock_embedding_service,
        synthesis_service=synthesizer,
    )

    request = QueryKnowledgeRequest(
        kb_id=kb_id,
        query="What are the security guidelines?",
        top_k=3,
    )

    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert isinstance(result.value, QueryKnowledgeResponse)
    assert len(result.value.results) == 1
    assert result.value.results[0].parent_chunk_id == "parent-1"
    assert result.value.results[0].relevance_score == 0.94
    assert "Relevant content about security." in result.value.answer
    mock_embedding_service.embed_texts.assert_awaited_once_with(
        ["What are the security guidelines?"]
    )
    mock_graph_store.query_hybrid.assert_awaited_once_with(kb_id, [0.1, 0.2, 0.3], 3)
