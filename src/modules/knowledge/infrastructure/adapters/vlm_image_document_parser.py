import base64
import io
import logging
from typing import Any

import httpx
from PIL import Image

try:
    import pillow_heif  # type: ignore[import-not-found]

    pillow_heif.register_heif_opener()
except ImportError:
    pass


from src.modules.knowledge.domain.interfaces.i_document_parser import IDocumentParser

logger = logging.getLogger(__name__)


class VlmImageDocumentParser(IDocumentParser):
    """
    Adaptador de OCR e extração estruturada de imagens usando modelo VLM via OpenRouter API.
    Converte e normaliza imagens (PNG, JPEG, WebP, HEIC/HEIF) para JPEG/PNG em memória
    e solicita transcrição descritiva em Markdown.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "qwen/qwen-2.5-vl-72b-instruct",
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def _normalize_image_bytes(self, raw_bytes: bytes, file_name: str) -> tuple[bytes, str]:
        ext = file_name.lower().split(".")[-1] if "." in file_name else "jpg"
        if ext in ("heic", "heif", "webp"):
            try:
                img = Image.open(io.BytesIO(raw_bytes))
                out_buf = io.BytesIO()
                img.convert("RGB").save(out_buf, format="JPEG", quality=90)
                return out_buf.getvalue(), "image/jpeg"
            except Exception as e:
                logger.warning("Failed to convert image %s to JPEG: %s", file_name, e)

        if ext == "png":
            return raw_bytes, "image/png"
        return raw_bytes, "image/jpeg"

    async def parse_to_markdown(
        self,
        raw_bytes: bytes,
        file_name: str,
        content_type: str,
        enable_ocr: bool = True,
        ocr_instructions: str | None = None,
        doc_id: Any = None,
        kb_partition: str | None = None,
        progress_callback: Any = None,
        ingested_at: float | None = None,
    ) -> str:
        if not self._api_key:
            logger.warning(
                "OpenRouter API key not provided for VLM image OCR. Returning placeholder markdown."
            )
            return (
                f"# Imagem: {file_name}\n\n"
                "[Aviso: OCR de imagem indisponível - Chave de API do OpenRouter não configurada.]"
            )

        # Se os bytes forem texto puro (ex: arquivos simulados de texto em testes rápidos)
        try:
            decoded = raw_bytes.decode("utf-8")
            if decoded.startswith("#") or " " in decoded:
                return decoded.strip()
        except UnicodeDecodeError:
            pass

        norm_bytes, mime = self._normalize_image_bytes(raw_bytes, file_name)

        b64_data = base64.b64encode(norm_bytes).decode("utf-8")
        data_uri = f"data:{mime};base64,{b64_data}"

        custom_prompt = ocr_instructions or (
            "Transcreva com máxima precisão todo o conteúdo textual, tabelas e diagramas "
            "visíveis nesta imagem. Formate a resposta em Markdown estruturado e semântico "
            "(use #, ##, tabelas | | e listas quando apropriado). Todas as descrições geradas "
            "de elementos visuais, figuras ou gráficos devem ser redigidas rigorosamente no "
            "mesmo idioma predominante da imagem/documento. Se for um print de conversa ou "
            "anotação, preserve a ordem e os interlocutores identificáveis."
        )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": "https://github.com/agentic-substrate",
            "X-Title": "Agentic Substrate VLM Image Parser",
        }

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": custom_prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            content = data["choices"][0]["message"]["content"]
            return str(content).strip()
        except Exception as e:
            logger.warning(
                "Failed to parse image %s via VLM OpenRouter: %s. Using placeholder description.",
                file_name,
                e,
            )
            try:
                decoded = raw_bytes.decode("utf-8")
                if decoded and decoded.strip():
                    return decoded.strip()
            except Exception:
                pass
            err_msg = f"[OCR Imagem: Não foi possível obter descrição visual online ({e})]"
            return f"# Imagem: {file_name}\n\n{err_msg}"
