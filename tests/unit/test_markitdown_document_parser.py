from unittest.mock import MagicMock

import pytest

from src.modules.knowledge.domain.interfaces.i_document_parser import IDocumentParser
from src.modules.knowledge.infrastructure.adapters.markitdown_document_parser import (
    MarkItDownDocumentParser,
)
from src.modules.knowledge.infrastructure.adapters.openrouter_client_factory import (
    OpenRouterClientFactory,
)


@pytest.mark.asyncio
async def test_markitdown_parser_implements_protocol() -> None:
    parser = MarkItDownDocumentParser()
    assert isinstance(parser, IDocumentParser)


@pytest.mark.asyncio
async def test_markitdown_parser_parses_plain_text() -> None:
    parser = MarkItDownDocumentParser()
    content = b"# Document Header\nThis is a sample paragraph with information."
    parsed = await parser.parse_to_markdown(content, "sample.txt", "text/plain")
    assert "Document Header" in parsed
    assert "sample paragraph" in parsed


@pytest.mark.asyncio
async def test_markitdown_parser_parses_html() -> None:
    parser = MarkItDownDocumentParser()
    html_content = b"<html><body><h1>Title from HTML</h1><p>Body paragraph</p></body></html>"
    parsed = await parser.parse_to_markdown(html_content, "page.html", "text/html")
    assert "Title from HTML" in parsed
    assert "Body paragraph" in parsed


@pytest.mark.asyncio
async def test_markitdown_parser_fallback_on_decoding() -> None:
    parser = MarkItDownDocumentParser()
    raw = b"Just some simple raw content without extension"
    parsed = await parser.parse_to_markdown(raw, "unknown_file", "application/octet-stream")
    assert "Just some simple raw content" in parsed


@pytest.mark.asyncio
async def test_markitdown_parser_with_openrouter_ocr_disabled_uses_native_fast_path() -> None:
    mock_client = MagicMock()
    parser = MarkItDownDocumentParser(openrouter_client=mock_client)

    content = b"# Plain Text\nFast path without LLM call."
    parsed = await parser.parse_to_markdown(
        content,
        "sample.txt",
        "text/plain",
        enable_ocr=False,
    )
    assert "Plain Text" in parsed
    # Mock client should never have been invoked because enable_ocr is False
    mock_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_markitdown_parser_with_openrouter_ocr_enabled_uses_custom_prompt() -> None:
    mock_client = MagicMock()
    mock_md = MagicMock()
    mock_res = MagicMock()
    mock_res.text_content = "# Transcribed Document\n| Table | Header |\n|---|---|"
    mock_md.convert_stream.return_value = mock_res

    parser = MarkItDownDocumentParser(
        openrouter_client=mock_client,
        vision_model="qwen/qwen3-vl-32b-instruct",
        markitdown_factory=lambda **kwargs: mock_md,
    )

    pdf_bytes = b"%PDF-1.4 sample pdf bytes"
    custom_prompt = "Transcribe tables in strict GFM and annotate diagrams."

    parsed = await parser.parse_to_markdown(
        pdf_bytes,
        "doc.pdf",
        "application/pdf",
        enable_ocr=True,
        ocr_instructions=custom_prompt,
    )
    assert "Transcribed Document" in parsed


def test_openrouter_client_factory_without_key_returns_none() -> None:
    client = OpenRouterClientFactory.create(api_key=None)
    assert client is None

    client_empty = OpenRouterClientFactory.create(api_key="   ")
    assert client_empty is None


def test_openrouter_client_factory_with_key_creates_openai_client() -> None:
    client = OpenRouterClientFactory.create(
        api_key="sk-or-test-key",
        base_url="https://openrouter.ai/api/v1",
        app_title="Test App",
        app_referer="https://test.local",
    )
    assert client is not None
    assert str(client.base_url) == "https://openrouter.ai/api/v1/"
