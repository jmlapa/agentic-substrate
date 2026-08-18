import asyncio
import base64
import threading
from io import BytesIO

import pypdfium2 as pdfium


class PdfPageRenderer:
    """
    Adaptador de infraestrutura para renderização de páginas PDF usando pypdfium2.
    Suporta renderização não-bloqueante dual-scale:
    - Baixa resolução (1.0x / ~72 DPI): Ideal para Synthetic ToC rápido e baixo consumo de tokens.
    - Alta resolução (2.0x / ~200 DPI): Ideal para transcrição de texto e OCR multimodal.
    Utiliza mutex interno para garantir isolamento seguro na engine nativa em C do PDFium.
    """

    def __init__(
        self,
        low_res_scale: float = 1.0,
        high_res_scale: float = 2.0,
        jpeg_quality: int = 80,
    ) -> None:
        self._low_res_scale = max(0.5, low_res_scale)
        self._high_res_scale = max(1.0, high_res_scale)
        self._jpeg_quality = max(10, min(100, jpeg_quality))
        self._lock = threading.Lock()

    def _render_page_sync(self, raw_bytes: bytes, page_index: int, scale: float) -> str:
        with self._lock:
            try:
                doc = pdfium.PdfDocument(raw_bytes)
                if page_index < 0 or page_index >= len(doc):
                    raise IndexError(f"Page index {page_index} out of range [0, {len(doc) - 1}]")
                page = doc[page_index]
                pil_image = page.render(scale=scale).to_pil()
                if pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")

                buffer = BytesIO()
                pil_image.save(buffer, format="JPEG", quality=self._jpeg_quality)
                return base64.b64encode(buffer.getvalue()).decode("utf-8")
            except Exception as e:
                if isinstance(e, IndexError):
                    raise
                raise ValueError(f"Arquivo PDF invalido ou corrompido: {e}") from e

    def _get_page_count_sync(self, raw_bytes: bytes) -> int:
        with self._lock:
            try:
                doc = pdfium.PdfDocument(raw_bytes)
                return len(doc)
            except Exception as e:
                raise ValueError(f"Arquivo PDF invalido ou corrompido: {e}") from e

    async def get_page_count(self, raw_bytes: bytes) -> int:
        """Retorna o número total de páginas do PDF de forma assíncrona."""
        return await asyncio.to_thread(self._get_page_count_sync, raw_bytes)

    async def render_page_low_res(self, raw_bytes: bytes, page_index: int) -> str:
        """Renderiza uma página em escala 1.0x retornando string Base64 JPEG."""
        return await asyncio.to_thread(
            self._render_page_sync, raw_bytes, page_index, self._low_res_scale
        )

    async def render_page_high_res(self, raw_bytes: bytes, page_index: int) -> str:
        """Renderiza uma página em escala 2.0x retornando string Base64 JPEG."""
        return await asyncio.to_thread(
            self._render_page_sync, raw_bytes, page_index, self._high_res_scale
        )
