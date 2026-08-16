import asyncio
import io
from pathlib import Path
from typing import Any

from markitdown import MarkItDown

from src.modules.knowledge.domain.interfaces.i_document_parser import IDocumentParser


class MarkItDownDocumentParser(IDocumentParser):
    def __init__(self, markitdown_instance: Any | None = None) -> None:
        self._markitdown = markitdown_instance or MarkItDown()

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

    def _convert_sync(self, raw_bytes: bytes, file_extension: str) -> str:
        try:
            stream = io.BytesIO(raw_bytes)
            result = self._markitdown.convert_stream(stream, file_extension=file_extension)
            text = result.text_content
            if text and text.strip():
                return text
        except Exception:
            pass

        # Fallback for plain text decoding
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return raw_bytes.decode("latin-1", errors="ignore")

    async def parse_to_markdown(
        self, raw_bytes: bytes, file_name: str, content_type: str
    ) -> str:
        file_extension = self._infer_extension(file_name, content_type)
        return await asyncio.to_thread(self._convert_sync, raw_bytes, file_extension)
