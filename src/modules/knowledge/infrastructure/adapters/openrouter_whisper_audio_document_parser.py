import io
import logging
from typing import Any

import httpx

from src.modules.knowledge.domain.interfaces.i_document_parser import IDocumentParser
from src.modules.knowledge.infrastructure.adapters.audio_transcription_formatter import (
    AudioTranscriptionFormatter,
)

logger = logging.getLogger(__name__)


class OpenRouterWhisperAudioDocumentParser(IDocumentParser):
    """
    Adaptador de transcrição de áudio usando o modelo openai/whisper-large-v3 via OpenRouter API.
    Converte o retorno verbose_json em Markdown com seções temporais bem delimitadas.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openai/whisper-large-v3",
        formatter: AudioTranscriptionFormatter | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._formatter = formatter or AudioTranscriptionFormatter()
        self._timeout = timeout

    async def parse_to_markdown(
        self,
        raw_bytes: bytes,
        file_name: str,
        content_type: str,
        enable_ocr: bool = False,
        ocr_instructions: str | None = None,
        doc_id: Any = None,
        kb_partition: str | None = None,
        progress_callback: Any = None,
        ingested_at: float | None = None,
    ) -> str:
        if not self._api_key:
            logger.warning(
                "OpenRouter API key not provided for audio transcription. "
                "Returning placeholder markdown."
            )
            return (
                f"# Transcrição de Áudio: {file_name}\n\n"
                "[Aviso: Transcrição de áudio indisponível - "
                "Chave de API do OpenRouter não configurada.]"
            )

        endpoint = f"{self._base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": "https://github.com/agentic-substrate",
            "X-Title": "Agentic Substrate Audio Parser",
        }

        files = {
            "file": (file_name, io.BytesIO(raw_bytes), content_type or "audio/mpeg"),
        }
        data = {
            "model": self._model,
            "response_format": "verbose_json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(endpoint, headers=headers, files=files, data=data)
                response.raise_for_status()
                payload = response.json()

            segments: list[dict[str, Any]] = payload.get("segments", [])
            if not segments and "text" in payload:
                segments = [{"start": 0.0, "end": 0.0, "text": payload["text"]}]

            return self._formatter.format_to_markdown(
                file_name=file_name,
                segments=segments,
                ingested_at=ingested_at,
            )
        except Exception as e:
            logger.error(
                "Failed to transcribe audio %s via OpenRouter Whisper: %s",
                file_name,
                e,
                exc_info=True,
            )
            return (
                f"# Transcrição de Áudio: {file_name}\n\n"
                f"[Erro ao processar transcrição de áudio via OpenRouter: {e}]"
            )
