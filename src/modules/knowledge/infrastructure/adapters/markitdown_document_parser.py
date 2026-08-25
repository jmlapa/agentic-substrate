import asyncio
import io
from pathlib import Path
from typing import Any

from markitdown import MarkItDown

from src.modules.knowledge.domain.interfaces.i_document_parser import IDocumentParser


class MarkItDownDocumentParser(IDocumentParser):
    """
    Adaptador de parsing de documentos para Markdown usando MarkItDown.
    Suporta fast-path nativo (custo zero e sem chamadas de rede para documentos puramente textuais)
    e modo multimodal com OpenRouter quando OCR/análise visual for solicitado pelo usuário.
    """

    def __init__(
        self,
        openrouter_client: Any | None = None,
        vision_model: str = "qwen/qwen3-vl-32b-instruct",
        default_prompt: str | None = None,
        markitdown_instance: Any | None = None,
        markitdown_factory: Any | None = None,
    ) -> None:
        self._openrouter_client = openrouter_client
        self._vision_model = vision_model
        self._default_prompt = default_prompt or (
            "Transcribe document faithfully into GitHub Flavored Markdown. "
            "Preserve tables, headings and lists, and provide descriptive "
            "text for figures and diagrams."
        )
        self._native_markitdown = markitdown_instance or MarkItDown()
        self._markitdown_factory = markitdown_factory

    def _infer_extension(self, file_name: str, content_type: str) -> str:
        ext = Path(file_name).suffix.lower()
        if ext:
            return ext
        mime_map = {
            "text/plain": ".txt",
            "text/markdown": ".md",
            "text/html": ".html",
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
            "text/csv": ".csv",
            "application/json": ".json",
        }
        return mime_map.get(content_type.lower(), ".txt")

    def _get_markitdown(self, enable_ocr: bool, ocr_instructions: str | None) -> Any:
        if not enable_ocr or not self._openrouter_client:
            return self._native_markitdown

        effective_prompt = (
            ocr_instructions.strip()
            if ocr_instructions and ocr_instructions.strip()
            else self._default_prompt
        )

        if self._markitdown_factory:
            return self._markitdown_factory(
                llm_client=self._openrouter_client,
                llm_model=self._vision_model,
                llm_prompt=effective_prompt,
            )

        try:
            return MarkItDown(
                llm_client=self._openrouter_client,
                llm_model=self._vision_model,
                llm_prompt=effective_prompt,
            )
        except Exception:
            return self._native_markitdown

    def _convert_sync(
        self,
        raw_bytes: bytes,
        file_extension: str,
        enable_ocr: bool,
        ocr_instructions: str | None,
    ) -> str:
        md_engine = self._get_markitdown(enable_ocr, ocr_instructions)
        try:
            stream = io.BytesIO(raw_bytes)
            result = md_engine.convert_stream(stream, file_extension=file_extension)
            text = getattr(result, "text_content", None)
            if text and text.strip():
                return str(text)
        except Exception:
            pass

        # Fallback for plain text decoding
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return raw_bytes.decode("latin-1", errors="ignore")

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
        **kwargs: Any,
    ) -> str:

        file_extension = self._infer_extension(file_name, content_type)
        return await asyncio.to_thread(
            self._convert_sync,
            raw_bytes,
            file_extension,
            enable_ocr,
            ocr_instructions,
        )
