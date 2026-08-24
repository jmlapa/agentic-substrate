from unittest.mock import AsyncMock, patch

import pytest

from src.modules.knowledge.infrastructure.adapters.vlm_image_document_parser import (
    VlmImageDocumentParser,
)


@pytest.mark.asyncio
async def test_vlm_image_parser_success() -> None:
    fake_response = {
        "choices": [
            {
                "message": {
                    "content": "# Diagrama\n\nO diagrama descreve os fluxos.",
                }
            }
        ]
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: fake_response
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        parser = VlmImageDocumentParser(api_key="sk-or-test")
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
            b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        md = await parser.parse_to_markdown(
            raw_bytes=png_bytes,
            file_name="diagram.png",
            content_type="image/png",
        )

    assert "# Diagrama" in md
    assert "O diagrama descreve os fluxos." in md


@pytest.mark.asyncio
async def test_vlm_image_parser_missing_api_key() -> None:
    parser = VlmImageDocumentParser(api_key=None)
    md = await parser.parse_to_markdown(
        raw_bytes=b"fake_img",
        file_name="screenshot.jpg",
        content_type="image/jpeg",
    )
    assert "[Aviso: OCR de imagem indisponível" in md


@pytest.mark.asyncio
async def test_vlm_image_parser_prompt_enforces_image_language() -> None:
    fake_response = {
        "choices": [
            {
                "message": {
                    "content": "# Output",
                }
            }
        ]
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: fake_response
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        parser = VlmImageDocumentParser(api_key="sk-or-test")
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
            b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        await parser.parse_to_markdown(
            raw_bytes=png_bytes,
            file_name="diagram.png",
            content_type="image/png",
        )

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        payload = call_kwargs["json"]
        text_prompt = payload["messages"][0]["content"][0]["text"]
        assert "mesmo idioma" in text_prompt
        assert payload.get("provider", {}).get("sort") == "throughput"
        assert payload.get("provider", {}).get("allow_fallbacks") is True
        assert payload.get("reasoning", {}).get("effort") == "none"
