import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pypdfium2 as pdfium
import pytest

from src.modules.knowledge.domain.entities.synthetic_document_toc import (
    SyntheticDocumentToc,
)
from src.modules.knowledge.infrastructure.adapters.pdf_page_renderer import (
    PdfPageRenderer,
)
from src.modules.knowledge.infrastructure.adapters.qwen_synthetic_toc_extractor import (
    QwenSyntheticTocExtractor,
)


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    doc = pdfium.PdfDocument.new()
    for _ in range(5):
        doc.new_page(width=200, height=200)
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def mock_openai_client() -> MagicMock:
    client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()

    json_toc = [
        {
            "type": "document_title",
            "markdown_level": "#",
            "title": "Sample Paper",
            "page": 1,
            "parent_section": None,
        },
        {
            "type": "section",
            "markdown_level": "##",
            "title": "1. Introduction",
            "page": 1,
            "parent_section": None,
        },
        {
            "type": "section",
            "markdown_level": "##",
            "title": "2. Methods",
            "page": 3,
            "parent_section": None,
        },
        {
            "type": "subsection",
            "markdown_level": "###",
            "title": "2.1 Study Design",
            "page": 4,
            "parent_section": "2. Methods",
        },
    ]

    mock_choice.message.content = f"```json\n{json.dumps(json_toc)}\n```"
    mock_response.choices = [mock_choice]
    client.chat.completions.create = AsyncMock(return_value=mock_response)
    return client


@pytest.mark.asyncio
async def test_qwen_synthetic_toc_extractor_success(
    sample_pdf_bytes: bytes, mock_openai_client: MagicMock
) -> None:
    renderer = PdfPageRenderer()
    extractor = QwenSyntheticTocExtractor(
        openai_client=mock_openai_client,
        page_renderer=renderer,
        vision_model="qwen/qwen3-vl-30b-a3b-instruct",
    )

    toc = await extractor.extract_toc(sample_pdf_bytes, batch_size=5)

    assert isinstance(toc, SyntheticDocumentToc)
    assert toc.total_headings == 4
    assert toc.document_title == "Sample Paper"
    expected_hierarchy = "# Sample Paper -> ## 2. Methods -> ### 2.1 Study Design"
    assert toc.get_active_hierarchy_for_page(4) == expected_hierarchy


@pytest.mark.asyncio
async def test_qwen_synthetic_toc_extractor_json_fallback(
    sample_pdf_bytes: bytes, mock_openai_client: MagicMock
) -> None:
    # Simula resposta sem markdown block, JSON puro
    raw_json = json.dumps(
        [
            {
                "type": "section",
                "markdown_level": "##",
                "title": "1. Introduction",
                "page": 1,
                "parent_section": None,
            }
        ]
    )
    mock_choice = MagicMock()
    mock_choice.message.content = raw_json
    mock_openai_client.chat.completions.create.return_value.choices = [mock_choice]

    extractor = QwenSyntheticTocExtractor(openai_client=mock_openai_client)
    toc = await extractor.extract_toc(sample_pdf_bytes, batch_size=10)

    assert toc.total_headings == 1
    assert toc.items[0].title == "1. Introduction"


@pytest.mark.asyncio
async def test_qwen_synthetic_toc_extractor_handles_empty_or_malformed_response(
    sample_pdf_bytes: bytes, mock_openai_client: MagicMock
) -> None:
    mock_choice = MagicMock()
    mock_choice.message.content = "Invalid non-json output from LLM"
    mock_openai_client.chat.completions.create.return_value.choices = [mock_choice]

    extractor = QwenSyntheticTocExtractor(openai_client=mock_openai_client)
    toc = await extractor.extract_toc(sample_pdf_bytes, batch_size=10)

    # Deve retornar ToC vazio sem quebrar a aplicação
    assert isinstance(toc, SyntheticDocumentToc)
    assert toc.total_headings == 0


@pytest.mark.asyncio
async def test_qwen_synthetic_toc_extractor_progress_callback(
    sample_pdf_bytes: bytes, mock_openai_client: MagicMock
) -> None:
    calls: list[tuple[int, int, str]] = []

    async def _callback(cur: int, tot: int, msg: str) -> None:
        calls.append((cur, tot, msg))

    extractor = QwenSyntheticTocExtractor(openai_client=mock_openai_client)
    await extractor.extract_toc(sample_pdf_bytes, batch_size=2, progress_callback=_callback)

    assert len(calls) == 3  # 5 pages / 2 = 3 batches
    assert calls[0][0] == 1
    assert calls[0][1] == 3
    assert "Lote 1/3" in calls[0][2]


@pytest.mark.asyncio
async def test_qwen_synthetic_toc_extractor_uses_cached_full_toc(
    sample_pdf_bytes: bytes, mock_openai_client: MagicMock, tmp_path: pytest.TempPathFactory
) -> None:
    from uuid import uuid4

    from src.modules.knowledge.domain.value_objects.hierarchical_toc_item import (
        HierarchicalTocItem,
    )
    from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
        LocalFileSystemStorageAdapter,
    )
    from src.modules.knowledge.infrastructure.adapters.toc_checkpoint_storage import (
        TocCheckpointStorage,
    )

    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    toc_storage = TocCheckpointStorage(storage=storage)

    partition = "kb-test"
    doc_id = uuid4()

    # Pre-popula ToC consolidado no cache
    cached_toc = SyntheticDocumentToc(
        items=[
            HierarchicalTocItem(
                type="document_title",
                markdown_level="#",
                title="Cached Doc",
                page=1,
            )
        ]
    )
    await toc_storage.save_toc(partition, doc_id, cached_toc)

    extractor = QwenSyntheticTocExtractor(
        openai_client=mock_openai_client,
        checkpoint_storage=toc_storage,
    )

    result = await extractor.extract_toc(
        sample_pdf_bytes,
        batch_size=2,
        doc_id=doc_id,
        kb_partition=partition,
    )

    assert result.document_title == "Cached Doc"
    # Nenhuma chamada à API foi feita!
    mock_openai_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_qwen_synthetic_toc_extractor_resumes_partial_batches(
    sample_pdf_bytes: bytes, mock_openai_client: MagicMock, tmp_path: pytest.TempPathFactory
) -> None:
    from uuid import uuid4

    from src.modules.knowledge.domain.value_objects.hierarchical_toc_item import (
        HierarchicalTocItem,
    )
    from src.modules.knowledge.domain.value_objects.toc_batch_state import (
        TocBatchState,
    )
    from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
        LocalFileSystemStorageAdapter,
    )
    from src.modules.knowledge.infrastructure.adapters.toc_checkpoint_storage import (
        TocCheckpointStorage,
    )

    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    toc_storage = TocCheckpointStorage(storage=storage)

    partition = "kb-test"
    doc_id = uuid4()

    # Pre-popula o Lote 1 no cache (páginas 1 e 2 de 5)
    batch_1_items = [
        HierarchicalTocItem(
            type="section",
            markdown_level="##",
            title="1. Cached Section",
            page=1,
        )
    ]
    batch_1_state = TocBatchState(
        active_section="1. Cached Section",
        active_subsection=None,
        active_markdown_level="##",
        last_page_processed=2,
    )
    await toc_storage.save_batch(partition, doc_id, 1, batch_1_items, batch_1_state)

    extractor = QwenSyntheticTocExtractor(
        openai_client=mock_openai_client,
        checkpoint_storage=toc_storage,
    )

    # 5 páginas em lotes de 2 = 3 lotes no total.
    # Lote 1 está em cache. Lotes 2 e 3 farão chamadas.
    result = await extractor.extract_toc(
        sample_pdf_bytes,
        batch_size=2,
        doc_id=doc_id,
        kb_partition=partition,
    )

    assert result.total_headings >= 1
    # Chamadas à API = 2 (para os lotes 2 e 3), economizando a chamada do Lote 1
    assert mock_openai_client.chat.completions.create.call_count == 2
    # ToC final consolidado foi salvo em cache
    assert await toc_storage.has_toc(partition, doc_id)
