from unittest.mock import AsyncMock, patch

import pytest

from src.modules.knowledge.infrastructure.adapters.openrouter_whisper_audio_document_parser import (
    OpenRouterWhisperAudioDocumentParser,
)


@pytest.mark.asyncio
async def test_parse_to_markdown_success() -> None:
    fake_response_data = {
        "text": "Esta é uma transcrição de teste.",
        "segments": [{"start": 0.0, "end": 4.5, "text": "Esta é uma transcrição de teste."}],
    }

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: fake_response_data
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        parser = OpenRouterWhisperAudioDocumentParser(api_key="sk-or-test")
        md = await parser.parse_to_markdown(
            raw_bytes=b"fake_audio_bytes",
            file_name="audio.mp3",
            content_type="audio/mpeg",
            ingested_at=1787238000.0,
        )

    assert "# Transcrição de Áudio: audio.mp3" in md
    assert "## [00:00 - 00:04]" in md
    assert "Esta é uma transcrição de teste." in md


@pytest.mark.asyncio
async def test_parse_to_markdown_missing_api_key_fallback() -> None:
    parser = OpenRouterWhisperAudioDocumentParser(api_key=None)
    md = await parser.parse_to_markdown(
        raw_bytes=b"fake_audio_bytes",
        file_name="audio.mp3",
        content_type="audio/mpeg",
    )
    assert "[Aviso: Transcrição de áudio indisponível" in md
