import pytest

from src.modules.knowledge.domain.interfaces.i_document_parser import IDocumentParser
from src.modules.knowledge.infrastructure.adapters.markitdown_document_parser import (
    MarkItDownDocumentParser,
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
