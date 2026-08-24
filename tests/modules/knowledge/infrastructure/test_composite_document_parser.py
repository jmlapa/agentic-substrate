from unittest.mock import AsyncMock

import pytest

from src.modules.knowledge.domain.interfaces.i_document_parser import IDocumentParser
from src.modules.knowledge.infrastructure.adapters.composite_document_parser import (
    CompositeDocumentParser,
)


@pytest.mark.asyncio
async def test_composite_parser_dispatches_to_image_parser() -> None:
    mock_doc = AsyncMock(spec=IDocumentParser)
    mock_image = AsyncMock(spec=IDocumentParser)
    mock_image.parse_to_markdown.return_value = "# Image Markdown"
    mock_audio = AsyncMock(spec=IDocumentParser)

    composite = CompositeDocumentParser(
        document_parser=mock_doc,
        image_parser=mock_image,
        audio_parser=mock_audio,
    )

    res = await composite.parse_to_markdown(
        raw_bytes=b"png_bytes",
        file_name="diagram.png",
        content_type="image/png",
    )

    assert res == "# Image Markdown"
    mock_image.parse_to_markdown.assert_awaited_once()
    mock_doc.parse_to_markdown.assert_not_awaited()
    mock_audio.parse_to_markdown.assert_not_awaited()


@pytest.mark.asyncio
async def test_composite_parser_dispatches_to_audio_parser() -> None:
    mock_doc = AsyncMock(spec=IDocumentParser)
    mock_image = AsyncMock(spec=IDocumentParser)
    mock_audio = AsyncMock(spec=IDocumentParser)
    mock_audio.parse_to_markdown.return_value = "# Audio Markdown"

    composite = CompositeDocumentParser(
        document_parser=mock_doc,
        image_parser=mock_image,
        audio_parser=mock_audio,
    )

    res = await composite.parse_to_markdown(
        raw_bytes=b"mp3_bytes",
        file_name="voice.m4a",
        content_type="audio/mp4",
        ingested_at=1787238000.0,
    )

    assert res == "# Audio Markdown"
    mock_audio.parse_to_markdown.assert_awaited_once()
    mock_doc.parse_to_markdown.assert_not_awaited()
    mock_image.parse_to_markdown.assert_not_awaited()


@pytest.mark.asyncio
async def test_composite_parser_dispatches_to_document_parser() -> None:
    mock_doc = AsyncMock(spec=IDocumentParser)
    mock_doc.parse_to_markdown.return_value = "# Doc Markdown"
    mock_image = AsyncMock(spec=IDocumentParser)
    mock_audio = AsyncMock(spec=IDocumentParser)

    composite = CompositeDocumentParser(
        document_parser=mock_doc,
        image_parser=mock_image,
        audio_parser=mock_audio,
    )

    res = await composite.parse_to_markdown(
        raw_bytes=b"pdf_bytes",
        file_name="article.pdf",
        content_type="application/pdf",
    )

    assert res == "# Doc Markdown"
    mock_doc.parse_to_markdown.assert_awaited_once()
    mock_image.parse_to_markdown.assert_not_awaited()
    mock_audio.parse_to_markdown.assert_not_awaited()
