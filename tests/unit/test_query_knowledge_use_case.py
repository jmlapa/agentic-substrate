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
    mock_embedding_service.embed_query.return_value = [0.1, 0.2, 0.3]

    expected_results = [
        HybridSearchResult(
            parent_chunk_id="parent-1",
            document_id="doc-123",
            document_name="lei_14133.pdf",
            header_path="# Section 1",
            parent_content="Relevant content about security.",
            relevance_score=0.94,
            retrieval_source="vector_match",
            prev_chunk_id="parent-0",
            next_chunk_id="parent-2",
            related_triples=["Lei 14.133 REGULA Contratos"],
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
        max_tokens_budget=3500,
        include_graph_triples=True,
    )

    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert isinstance(result.value, QueryKnowledgeResponse)
    assert len(result.value.results) == 1
    assert result.value.results[0].parent_chunk_id == "parent-1"
    assert result.value.results[0].document_name == "lei_14133.pdf"
    assert result.value.results[0].related_triples == ["Lei 14.133 REGULA Contratos"]
    assert result.value.results[0].prev_chunk_id == "parent-0"
    assert result.value.results[0].next_chunk_id == "parent-2"
    assert result.value.results[0].relevance_score == 0.94
    assert result.value.total_tokens_estimated > 0
    assert "retrieval_trace" in result.value.model_dump()
    assert result.value.retrieval_trace["candidate_k"] == 50
    assert result.value.retrieval_trace["top_k"] == 3
    assert "Relevant content about security." in result.value.answer
    mock_embedding_service.embed_query.assert_awaited_once_with("What are the security guidelines?")
    # Candidate oversampling: candidate_k = max(3 * 4, 50) = 50
    mock_graph_store.query_hybrid.assert_awaited_once_with(kb_id, [0.1, 0.2, 0.3], 3, 50)


@pytest.mark.asyncio
async def test_query_knowledge_use_case_retrieve_mode() -> None:
    mock_graph_store = AsyncMock(spec=IGraphStore)
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)
    mock_synthesizer = AsyncMock()

    kb_id = uuid4()
    mock_embedding_service.embed_query.return_value = [0.5, 0.5]

    expected_results = [
        HybridSearchResult(
            parent_chunk_id="parent-fast",
            document_id="doc-fast",
            document_name="doc.md",
            header_path="# Direct Data",
            parent_content="Fast raw content.",
            relevance_score=0.99,
            retrieval_source="vector_match",
            related_entities=[],
        )
    ]
    mock_graph_store.query_hybrid.return_value = expected_results

    use_case = QueryKnowledgeUseCase(
        graph_store=mock_graph_store,
        embedding_service=mock_embedding_service,
        synthesis_service=mock_synthesizer,
    )

    request = QueryKnowledgeRequest(
        kb_id=kb_id,
        query="Raw query",
        top_k=1,
        mode="retrieve",
    )

    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert len(result.value.results) == 1
    assert "Modo retrieve: 1 evidências recuperadas" in result.value.answer
    assert result.value.retrieval_trace["mode"] == "retrieve"
    assert result.value.retrieval_trace["candidate_k"] == 50  # max(1 * 4, 50) = 50
    mock_embedding_service.embed_query.assert_awaited_once_with("Raw query")
    mock_graph_store.query_hybrid.assert_awaited_once_with(kb_id, [0.5, 0.5], 1, 50)
    # Ensure synthesis_service was NOT invoked
    mock_synthesizer.synthesize_answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_knowledge_use_case_empty_results() -> None:
    mock_graph_store = AsyncMock(spec=IGraphStore)
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)

    kb_id = uuid4()
    mock_embedding_service.embed_query.return_value = [0.1, 0.1]
    mock_graph_store.query_hybrid.return_value = []

    use_case = QueryKnowledgeUseCase(
        graph_store=mock_graph_store,
        embedding_service=mock_embedding_service,
        synthesis_service=None,
    )

    request = QueryKnowledgeRequest(
        kb_id=kb_id,
        query="Non-existent info",
        top_k=5,
    )

    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert len(result.value.results) == 0
    assert "Nenhum documento ou contexto relevante foi encontrado" in result.value.answer
    assert result.value.total_tokens_estimated == 0


@pytest.mark.asyncio
async def test_query_knowledge_use_case_dynamic_token_budgeting() -> None:
    mock_graph_store = AsyncMock(spec=IGraphStore)
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)
    synthesizer = InMemoryRagSynthesizer()

    kb_id = uuid4()
    mock_embedding_service.embed_query.return_value = [0.1, 0.1]

    # 3 chunks with 1000 characters each (~250 tokens each = 750 tokens total)
    # But request max_tokens_budget is set to 300 tokens
    expected_results = [
        HybridSearchResult(
            parent_chunk_id="parent-1",
            document_id="doc-1",
            document_name="doc1.md",
            header_path="# Section 1",
            parent_content="A" * 600,
            relevance_score=0.95,
        ),
        HybridSearchResult(
            parent_chunk_id="parent-2",
            document_id="doc-1",
            document_name="doc1.md",
            header_path="# Section 2",
            parent_content="B" * 600,
            relevance_score=0.90,
        ),
    ]
    mock_graph_store.query_hybrid.return_value = expected_results

    use_case = QueryKnowledgeUseCase(
        graph_store=mock_graph_store,
        embedding_service=mock_embedding_service,
        synthesis_service=synthesizer,
    )

    # Budget strictly 200 tokens (approx 800 chars)
    request = QueryKnowledgeRequest(
        kb_id=kb_id,
        query="Test budget",
        top_k=2,
        max_tokens_budget=200,
    )

    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert result.value.total_tokens_estimated <= 200
    assert result.value.retrieval_trace["token_budget_limit"] == 200
    assert result.value.retrieval_trace["budget_truncated"] is True


@pytest.mark.asyncio
async def test_query_knowledge_use_case_discards_micro_chunks_below_threshold() -> None:
    mock_graph_store = AsyncMock(spec=IGraphStore)
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)
    synthesizer = InMemoryRagSynthesizer()

    kb_id = uuid4()
    mock_embedding_service.embed_query.return_value = [0.1, 0.1]

    # Chunk 1 consumes 180 tokens (out of 200 budget).
    # Remaining budget is 20 tokens. Since 20 tokens < 50 min_useful_tokens,
    # chunk 2 is completely omitted instead of producing a 10-char useless fragment.
    expected_results = [
        HybridSearchResult(
            parent_chunk_id="parent-1",
            document_id="doc-1",
            document_name="doc1.md",
            header_path="# Section 1",
            parent_content="A" * 594,  # 594 / 3.3 = 180 tokens
            relevance_score=0.95,
        ),
        HybridSearchResult(
            parent_chunk_id="parent-2",
            document_id="doc-1",
            document_name="doc1.md",
            header_path="# Section 2",
            parent_content="B" * 500,
            relevance_score=0.90,
        ),
    ]
    mock_graph_store.query_hybrid.return_value = expected_results

    use_case = QueryKnowledgeUseCase(
        graph_store=mock_graph_store,
        embedding_service=mock_embedding_service,
        synthesis_service=synthesizer,
    )

    request = QueryKnowledgeRequest(
        kb_id=kb_id,
        query="Test micro chunk discard",
        top_k=2,
        max_tokens_budget=200,
    )

    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert len(result.value.results) == 1
    assert result.value.results[0].parent_chunk_id == "parent-1"
    assert result.value.retrieval_trace["budget_truncated"] is True
    assert result.value.total_tokens_estimated <= 200


@pytest.mark.asyncio
async def test_query_knowledge_use_case_chunk_zero_never_dropped() -> None:
    mock_graph_store = AsyncMock(spec=IGraphStore)
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)
    synthesizer = InMemoryRagSynthesizer()

    kb_id = uuid4()
    mock_embedding_service.embed_query.return_value = [0.1, 0.1]

    # Chunk 1 has 300 tokens (990 chars), but budget is only 40 tokens (< 50 MIN_USEFUL_TOKENS)
    # Even with budget < MIN_USEFUL_TOKENS, chunk #1 must be preserved and truncated, NEVER dropped!
    expected_results = [
        HybridSearchResult(
            parent_chunk_id="parent-champion",
            document_id="doc-1",
            document_name="doc1.md",
            header_path="# Section 1",
            parent_content="A" * 990,
            relevance_score=0.99,
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
        query="Tight budget",
        top_k=1,
        max_tokens_budget=50,
    )

    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert len(result.value.results) == 1
    assert result.value.results[0].parent_chunk_id == "parent-champion"
    assert result.value.retrieval_trace["budget_truncated"] is True


@pytest.mark.asyncio
async def test_query_knowledge_use_case_flags_synthesis_error_in_trace() -> None:
    mock_graph_store = AsyncMock(spec=IGraphStore)
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)
    mock_synthesizer = AsyncMock()
    mock_synthesizer.synthesize_answer.return_value = (
        "Erro na comunicação com o LLM via OpenRouter (Rate limit). "
        "Evidências encontradas (1 resultados disponíveis no inspetor)."
    )

    kb_id = uuid4()
    mock_embedding_service.embed_query.return_value = [0.1, 0.1]
    mock_graph_store.query_hybrid.return_value = [
        HybridSearchResult(
            parent_chunk_id="p1",
            document_id="d1",
            document_name="doc.md",
            header_path="# Sec",
            parent_content="Content text",
            relevance_score=0.9,
        )
    ]

    use_case = QueryKnowledgeUseCase(
        graph_store=mock_graph_store,
        embedding_service=mock_embedding_service,
        synthesis_service=mock_synthesizer,
    )

    request = QueryKnowledgeRequest(kb_id=kb_id, query="Query with error", top_k=1)
    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert result.value.retrieval_trace["synthesis_error"] is True


def test_query_knowledge_request_and_dto_defaults_and_limits() -> None:
    from pydantic import ValidationError

    from src.api_gateway.dtos.query_knowledge_dto import QueryKnowledgeDTO

    kb_id = uuid4()

    # 1. Defaults should be the maximum allowed values: top_k = 20, max_tokens_budget = 32000
    req_default = QueryKnowledgeRequest(kb_id=kb_id, query="Default check")
    assert req_default.top_k == 20
    assert req_default.max_tokens_budget == 32000
    assert req_default.mode == "synthesis"
    assert req_default.include_graph_triples is True

    dto_default = QueryKnowledgeDTO(query="Default check")
    assert dto_default.top_k == 20
    assert dto_default.max_tokens_budget == 32000
    assert dto_default.mode == "synthesis"
    assert dto_default.include_graph_triples is True

    # 2. Validation boundary enforcement for top_k (1 <= top_k <= 20)
    with pytest.raises(ValidationError):
        QueryKnowledgeRequest(kb_id=kb_id, query="Invalid top_k", top_k=21)
    with pytest.raises(ValidationError):
        QueryKnowledgeRequest(kb_id=kb_id, query="Invalid top_k", top_k=0)
    with pytest.raises(ValidationError):
        QueryKnowledgeDTO(query="Invalid top_k", top_k=21)
    with pytest.raises(ValidationError):
        QueryKnowledgeDTO(query="Invalid top_k", top_k=0)

    # 3. Validation boundary enforcement for max_tokens_budget (50 <= max_tokens_budget <= 32000)
    with pytest.raises(ValidationError):
        QueryKnowledgeRequest(kb_id=kb_id, query="Invalid budget", max_tokens_budget=32001)
    with pytest.raises(ValidationError):
        QueryKnowledgeRequest(kb_id=kb_id, query="Invalid budget", max_tokens_budget=49)
    with pytest.raises(ValidationError):
        QueryKnowledgeDTO(query="Invalid budget", max_tokens_budget=32001)
    with pytest.raises(ValidationError):
        QueryKnowledgeDTO(query="Invalid budget", max_tokens_budget=49)


@pytest.mark.asyncio
async def test_query_knowledge_use_case_uses_maximum_defaults() -> None:
    mock_graph_store = AsyncMock(spec=IGraphStore)
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)
    synthesizer = InMemoryRagSynthesizer()

    kb_id = uuid4()
    mock_embedding_service.embed_query.return_value = [0.1, 0.2]
    mock_graph_store.query_hybrid.return_value = []

    use_case = QueryKnowledgeUseCase(
        graph_store=mock_graph_store,
        embedding_service=mock_embedding_service,
        synthesis_service=synthesizer,
    )

    request = QueryKnowledgeRequest(kb_id=kb_id, query="Check default max parameters")
    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert result.value.retrieval_trace["top_k"] == 20
    assert result.value.retrieval_trace["token_budget_limit"] == 32000
    assert result.value.retrieval_trace["candidate_k"] == 80  # max(20 * 4, 50) = 80
    mock_graph_store.query_hybrid.assert_awaited_once_with(kb_id, [0.1, 0.2], 20, 80)
    mock_embedding_service.embed_query.assert_awaited_once_with("Check default max parameters")


@pytest.mark.asyncio
async def test_query_knowledge_use_case_candidate_k_minimum_oversampling() -> None:
    mock_graph_store = AsyncMock(spec=IGraphStore)
    mock_embedding_service = AsyncMock(spec=IEmbeddingService)
    synthesizer = InMemoryRagSynthesizer()

    kb_id = uuid4()
    mock_embedding_service.embed_query.return_value = [0.1, 0.2]
    mock_graph_store.query_hybrid.return_value = []

    use_case = QueryKnowledgeUseCase(
        graph_store=mock_graph_store,
        embedding_service=mock_embedding_service,
        synthesis_service=synthesizer,
    )

    # Even for top_k=1, candidate_k should be at least 50
    request = QueryKnowledgeRequest(kb_id=kb_id, query="Minimum oversampling test", top_k=1)
    result = await use_case.execute(request)

    assert isinstance(result, Ok)
    assert result.value.retrieval_trace["top_k"] == 1
    assert result.value.retrieval_trace["candidate_k"] == 50  # max(1 * 4, 50) = 50
    mock_graph_store.query_hybrid.assert_awaited_once_with(kb_id, [0.1, 0.2], 1, 50)
    mock_embedding_service.embed_query.assert_awaited_once_with("Minimum oversampling test")
