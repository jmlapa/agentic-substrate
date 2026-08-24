from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pypdfium2 as pdfium
import pytest

from src.modules.knowledge.domain.entities.synthetic_document_toc import (
    SyntheticDocumentToc,
)
from src.modules.knowledge.domain.value_objects.hierarchical_toc_item import (
    HierarchicalTocItem,
)
from src.modules.knowledge.infrastructure.adapters.parallel_vlm_document_parser import (
    ParallelVlmDocumentParser,
)


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    doc = pdfium.PdfDocument.new()
    for _ in range(2):
        doc.new_page(width=200, height=200)
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def mock_toc() -> SyntheticDocumentToc:
    return SyntheticDocumentToc(
        items=[
            HierarchicalTocItem(
                type="document_title",
                markdown_level="#",
                title="Sample Doc",
                page=1,
                parent_section=None,
            ),
            HierarchicalTocItem(
                type="section",
                markdown_level="##",
                title="1. Introduction",
                page=1,
                parent_section=None,
            ),
            HierarchicalTocItem(
                type="section",
                markdown_level="##",
                title="2. Methods",
                page=2,
                parent_section=None,
            ),
        ]
    )


@pytest.mark.asyncio
async def test_fast_path_non_ocr(sample_pdf_bytes: bytes) -> None:
    parser = ParallelVlmDocumentParser()
    # Quando enable_ocr=False, não chama o LLM
    result = await parser.parse_to_markdown(
        raw_bytes=b"Hello plain text",
        file_name="sample.txt",
        content_type="text/plain",
        enable_ocr=False,
    )
    assert "Hello plain text" in result


@pytest.mark.asyncio
async def test_parallel_vlm_ocr_success(
    sample_pdf_bytes: bytes, mock_toc: SyntheticDocumentToc
) -> None:
    mock_client = MagicMock()
    mock_choice1 = MagicMock()
    mock_choice1.message.content = "## 1. Introduction\n\nThis is page 1 content."
    mock_choice2 = MagicMock()
    mock_choice2.message.content = "## 2. Methods\n\nThis is page 2 content."

    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            MagicMock(choices=[mock_choice1]),
            MagicMock(choices=[mock_choice2]),
        ]
    )

    mock_toc_extractor = MagicMock()
    mock_toc_extractor.extract_toc = AsyncMock(return_value=mock_toc)

    parser = ParallelVlmDocumentParser(
        openai_client=mock_client,
        toc_extractor=mock_toc_extractor,
        max_concurrency=2,
    )

    markdown = await parser.parse_to_markdown(
        raw_bytes=sample_pdf_bytes,
        file_name="paper.pdf",
        content_type="application/pdf",
        enable_ocr=True,
    )

    assert "## 1. Introduction" in markdown
    assert "## 2. Methods" in markdown
    assert "<!-- PAGE 1 -->" not in markdown
    assert "<!-- PAGE 2 -->" not in markdown
    assert mock_toc_extractor.extract_toc.called


@pytest.mark.asyncio
async def test_parallel_vlm_parser_fast_path_when_all_pages_cached(
    sample_pdf_bytes: bytes, tmp_path: pytest.TempPathFactory
) -> None:
    from uuid import uuid4

    from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
        LocalFileSystemStorageAdapter,
    )
    from src.modules.knowledge.infrastructure.adapters.page_checkpoint_storage import (
        PageCheckpointStorage,
    )

    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    page_storage = PageCheckpointStorage(storage=storage)

    partition = "kb-test"
    doc_id = uuid4()

    # Pre-popula 100% das páginas (páginas 1 e 2 de 2)
    await page_storage.save_page(partition, doc_id, 1, "Cached Page 1 Content")
    await page_storage.save_page(partition, doc_id, 2, "Cached Page 2 Content")

    mock_client = MagicMock()
    mock_toc_extractor = MagicMock()

    parser = ParallelVlmDocumentParser(
        openai_client=mock_client,
        toc_extractor=mock_toc_extractor,
        checkpoint_storage=page_storage,
    )

    progress_calls: list[tuple[int, int, str]] = []

    async def _progress(cur: int, tot: int, msg: str) -> None:
        progress_calls.append((cur, tot, msg))

    markdown = await parser.parse_to_markdown(
        raw_bytes=sample_pdf_bytes,
        file_name="paper.pdf",
        content_type="application/pdf",
        enable_ocr=True,
        doc_id=doc_id,
        kb_partition=partition,
        progress_callback=_progress,
    )

    assert "Cached Page 1 Content" in markdown
    assert "Cached Page 2 Content" in markdown
    # Fast-Path: ToC e chamadas à LLM foram ignoradas
    mock_toc_extractor.extract_toc.assert_not_called()
    mock_client.chat.completions.create.assert_not_called()
    assert len(progress_calls) == 1
    assert progress_calls[0][0] == 2
    assert "100% recuperado" in progress_calls[0][2]


def test_dedup_removes_identical_adjacent() -> None:
    parser = ParallelVlmDocumentParser()
    input_md = "## Intro\n\n## Intro\n\nSome content"
    expected = "## Intro\n\nSome content"
    assert parser._dedup_adjacent_headers(input_md) == expected


def test_dedup_preserves_distinct_adjacent() -> None:
    parser = ParallelVlmDocumentParser()
    input_md = "## Intro\n\n## Methods\n\nContent"
    # Both headings should remain
    assert parser._dedup_adjacent_headers(input_md) == input_md


def test_dedup_ignores_non_adjacent() -> None:
    parser = ParallelVlmDocumentParser()
    input_md = "## Intro\n\nParagraph text here.\n\n## Intro\n\nMore content"
    # Since a non‑heading line separates them, both should stay
    assert parser._dedup_adjacent_headers(input_md) == input_md


def test_normalize_removes_page_markers() -> None:
    parser = ParallelVlmDocumentParser()
    raw = "<!-- PAGE 1 -->\n\nContent of page one.\n\n<!-- PAGE 2 -->\n\nContent of page two."
    result = parser._normalize_markdown(raw)
    assert "<!-- PAGE" not in result
    assert "Content of page one." in result
    assert "Content of page two." in result


def test_normalize_removes_error_markers() -> None:
    parser = ParallelVlmDocumentParser()
    raw = "Good content.\n\n<!-- [Erro no OCR da Página 3: timeout] -->\n\nMore content."
    result = parser._normalize_markdown(raw)
    assert "<!-- [Erro" not in result
    assert "Good content." in result
    assert "More content." in result


def test_normalize_collapses_excess_newlines() -> None:
    parser = ParallelVlmDocumentParser()
    raw = "Paragraph one.\n\n\n\n\nParagraph two."
    result = parser._normalize_markdown(raw)
    assert "\n\n\n" not in result
    assert "Paragraph one." in result
    assert "Paragraph two." in result


def test_normalize_deduplicates_adjacent_headings() -> None:
    parser = ParallelVlmDocumentParser()
    raw = (
        "<!-- PAGE 1 -->\n\n"
        "## Introduction\n\n"
        "<!-- PAGE 2 -->\n\n"
        "## Introduction\n\n"
        "Actual content."
    )
    result = parser._normalize_markdown(raw)
    assert result.count("## Introduction") == 1
    assert "Actual content." in result


def test_normalize_dedup_is_case_insensitive() -> None:
    parser = ParallelVlmDocumentParser()
    raw = "## INTRODUCTION\n\n## Introduction\n\nContent."
    result = parser._normalize_markdown(raw)
    assert result.count("INTRODUCTION") + result.count("Introduction") == 1
    assert "Content." in result


def test_normalize_preserves_table_rows() -> None:
    parser = ParallelVlmDocumentParser()
    raw = (
        "<!-- PAGE 1 -->\n\n"
        "## Results\n\n"
        "| Col A | Col B |\n"
        "|-------|-------|\n"
        "| val1  | val2  |\n\n"
        "<!-- PAGE 2 -->\n\n"
        "| val3  | val4  |"
    )
    result = parser._normalize_markdown(raw)
    assert "| Col A | Col B |" in result
    assert "| val3  | val4  |" in result
    assert "<!-- PAGE" not in result


def test_normalize_strips_leading_trailing_whitespace() -> None:
    parser = ParallelVlmDocumentParser()
    raw = "\n\n<!-- PAGE 1 -->\n\nContent here.\n\n"
    result = parser._normalize_markdown(raw)
    assert result == result.strip()
    assert result.startswith("Content here.")


@pytest.mark.asyncio
async def test_parallel_vlm_parser_monotonic_progress_callback(
    sample_pdf_bytes: bytes, mock_toc: SyntheticDocumentToc
) -> None:
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Sample transcribed content"
    mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[mock_choice]))

    mock_toc_extractor = MagicMock()
    mock_toc_extractor.extract_toc = AsyncMock(return_value=mock_toc)

    parser = ParallelVlmDocumentParser(
        openai_client=mock_client,
        toc_extractor=mock_toc_extractor,
        max_concurrency=2,
    )

    progress_history: list[int] = []
    progress_messages: list[str] = []

    async def _progress(cur: int, tot: int, msg: str) -> None:
        progress_history.append(cur)
        progress_messages.append(msg)

    await parser.parse_to_markdown(
        raw_bytes=sample_pdf_bytes,
        file_name="paper.pdf",
        content_type="application/pdf",
        enable_ocr=True,
        progress_callback=_progress,
    )

    # Progresso foi estritamente monotônico: [1, 2]
    assert progress_history == [1, 2]
    assert len(progress_messages) == 2
    assert progress_messages[0] == "Processando OCR: 1/2 páginas concluídas"
    assert progress_messages[1] == "Processando OCR: 2/2 páginas concluídas"


@pytest.mark.asyncio
async def test_transcribe_system_prompt_contains_continuity_rules(
    sample_pdf_bytes: bytes,
) -> None:
    import asyncio

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Page content"
    mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[mock_choice]))

    parser = ParallelVlmDocumentParser(openai_client=mock_client)
    semaphore = asyncio.Semaphore(1)

    await parser._transcribe_single_page(
        raw_bytes=sample_pdf_bytes,
        page_num=1,
        total_pages=2,
        hierarchy_hint="Section 1",
        effective_prompt="Default prompt",
        semaphore=semaphore,
    )

    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    system_message = next(msg["content"] for msg in messages if msg["role"] == "system")

    assert "Continuidade de Hierarquia" in system_message
    assert "Continuidade de Texto" in system_message
    assert "Tabelas Inter-Página" in system_message
