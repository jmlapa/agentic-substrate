import asyncio
import io
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any
from uuid import UUID

from markitdown import MarkItDown

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)
from src.modules.knowledge.domain.interfaces.i_document_parser import (
    IDocumentParser,
)
from src.modules.knowledge.domain.interfaces.i_synthetic_toc_extractor import (
    ISyntheticTocExtractor,
)
from src.modules.knowledge.infrastructure.adapters.page_checkpoint_storage import (
    PageCheckpointStorage,
)
from src.modules.knowledge.infrastructure.adapters.pdf_page_renderer import (
    PdfPageRenderer,
)


class ParallelVlmDocumentParser(IDocumentParser):
    """
    Parser de documentos com suporte a Two-Pass OCR e Checkpoints Atômicos por Página.
    Garante desperdício zero de tokens ao reutilizar páginas já transcritas em disco.
    """

    def __init__(
        self,
        openai_client: Any | None = None,
        toc_extractor: ISyntheticTocExtractor | None = None,
        page_renderer: PdfPageRenderer | None = None,
        vision_model: str = "qwen/qwen3-vl-32b-instruct",
        default_prompt: str | None = None,
        max_concurrency: int = 5,
        rate_limiter: AsyncTokenBucketLimiter | None = None,
        native_markitdown: Any | None = None,
        checkpoint_storage: PageCheckpointStorage | None = None,
    ) -> None:
        self._client = openai_client
        self._toc_extractor = toc_extractor
        self._renderer = page_renderer or PdfPageRenderer()
        self._vision_model = vision_model
        self._default_prompt = default_prompt or (
            "Transcribe document faithfully into GitHub Flavored Markdown (GFM). "
            "Preserve tables, headings and lists, and provide descriptive "
            "text for figures and diagrams."
        )
        self._max_concurrency = max(1, max_concurrency)
        self._semaphore = asyncio.Semaphore(self._max_concurrency)
        self._limiter = rate_limiter
        self._native_markitdown = native_markitdown or MarkItDown()
        self._checkpoint_storage = checkpoint_storage

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

    def _convert_fast_path_sync(self, raw_bytes: bytes, file_extension: str) -> str:
        try:
            stream = io.BytesIO(raw_bytes)
            result = self._native_markitdown.convert_stream(stream, file_extension=file_extension)
            text = getattr(result, "text_content", None)
            if text and text.strip():
                return str(text)
        except Exception:
            pass

        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return raw_bytes.decode("latin-1", errors="ignore")

    async def _transcribe_single_page(
        self,
        raw_bytes: bytes,
        page_num: int,
        total_pages: int,
        hierarchy_hint: str,
        effective_prompt: str,
        semaphore: asyncio.Semaphore,
        kb_partition: str | None = None,
        doc_id: UUID | None = None,
    ) -> str:
        # 1. Checagem de Checkpoint em Disco (Zero Token Waste)
        if self._checkpoint_storage and kb_partition and doc_id:
            if await self._checkpoint_storage.has_page(kb_partition, doc_id, page_num):
                cached = await self._checkpoint_storage.get_page(kb_partition, doc_id, page_num)
                if cached is not None:
                    return cached

        async with semaphore:
            b64_img = await self._renderer.render_page_high_res(raw_bytes, page_num - 1)

            system_prompt = (
                "Você é um especialista em OCR e estruturação de documentos em Markdown.\n"
                "SEU OBJETIVO:\n"
                "Transcrever EXCLUSIVAMENTE a página alvo para GitHub Flavored Markdown (GFM).\n\n"
                "REGRAS RÍGIDAS:\n"
                "1. Hierarquia de Cabeçalhos:\n"
                f"   - Contexto da linhagem ativa: '{hierarchy_hint}'\n"
                "   - Use o nível correto de cabeçalho (#, ##, ###, ####). "
                "Não invente títulos inexistentes na página.\n"
                "2. Tabelas:\n"
                "   - Converta todas as tabelas em Markdown GFM puro (| Col 1 | Col 2 |).\n"
                "3. Figuras e Elementos Visuais:\n"
                "   - Para cada figura ou gráfico, use a anotação:\n"
                "     > **[Figura X: Título/Legenda]**\n"
                "     > *Descrição visual*: [Descreva detalhadamente o gráfico e tendências].\n"
                "4. Retorne APENAS o código Markdown sem blocos ```markdown envolventes."
            )

            user_content: list[dict[str, Any]] = [
                {
                    "type": "text",
                    "text": (
                        f"--- PÁGINA {page_num} de {total_pages} ---\n"
                        f"Hierarquia estrutural ativa: {hierarchy_hint}\n"
                        f"Instruções do usuário: {effective_prompt}\n"
                        f"Transcreva com fidelidade a Página {page_num}:"
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                },
            ]

            if self._limiter:
                await self._limiter.acquire(estimated_tokens=1500)

            if not self._client:
                return f"<!-- [Página {page_num} não transcrita: cliente não configurado] -->"

            try:
                response = await self._client.chat.completions.create(
                    model=self._vision_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.0,
                    extra_body={
                        "provider": {
                            "sort": "throughput",
                            "allow_fallbacks": True,
                        },
                        "reasoning": {
                            "effort": "none",
                            "exclude": True,
                        },
                    },
                )
                page_md = str(response.choices[0].message.content or "").strip()

                # 2. Salva Checkpoint imediatamente após sucesso
                if self._checkpoint_storage and kb_partition and doc_id:
                    await self._checkpoint_storage.save_page(
                        kb_partition, doc_id, page_num, page_md
                    )

                return page_md
            except Exception as e:
                return f"<!-- [Erro no OCR da Página {page_num}: {e}] -->"

    async def parse_to_markdown(
        self,
        raw_bytes: bytes,
        file_name: str,
        content_type: str,
        enable_ocr: bool = False,
        ocr_instructions: str | None = None,
        doc_id: Any = None,
        kb_partition: str | None = None,
        progress_callback: (Callable[[int, int, str], Coroutine[Any, Any, None]] | None) = None,
    ) -> str:
        file_extension = self._infer_extension(file_name, content_type)
        is_pdf = file_extension == ".pdf" or content_type.lower() == "application/pdf"

        # Fast-Path: Arquivos não-PDF ou OCR desativado
        if not enable_ocr or not self._client or not is_pdf:
            return await asyncio.to_thread(self._convert_fast_path_sync, raw_bytes, file_extension)

        total_pages = await self._renderer.get_page_count(raw_bytes)
        if total_pages <= 0:
            return await asyncio.to_thread(self._convert_fast_path_sync, raw_bytes, file_extension)

        # 0. Fast-Path: Verifica se 100% das páginas de OCR já existem no cache
        if self._checkpoint_storage and kb_partition and doc_id:
            completed_pages_set = await self._checkpoint_storage.get_completed_pages(
                kb_partition, doc_id
            )
            if len(completed_pages_set) == total_pages and all(
                p in completed_pages_set for p in range(1, total_pages + 1)
            ):
                # Pula ToC completamente e monta o Markdown diretamente do disco (0 tokens)
                if progress_callback:
                    msg = (
                        f"Documento 100% recuperado do cache de OCR "
                        f"({total_pages}/{total_pages} páginas)"
                    )
                    await progress_callback(total_pages, total_pages, msg)
                cached_blocks: list[str] = []
                for p in range(1, total_pages + 1):
                    p_content = await self._checkpoint_storage.get_page(kb_partition, doc_id, p)
                    cached_blocks.append(f"<!-- PAGE {p} -->\n{p_content or ''}")
                return "\n\n".join(cached_blocks)

        # Passo 1: Descoberta Estrutural (Synthetic ToC com Checkpoints)
        toc = None
        if self._toc_extractor:
            try:
                toc = await self._toc_extractor.extract_toc(
                    raw_bytes,
                    progress_callback=progress_callback,
                    doc_id=doc_id,
                    kb_partition=kb_partition,
                )
            except Exception:
                toc = None

        effective_prompt = (
            ocr_instructions.strip()
            if ocr_instructions and ocr_instructions.strip()
            else self._default_prompt
        )

        # Passo 2: Transcrição Paralela Concorrente com Fila de Workers e Telemetria Monotônica
        queue: asyncio.Queue[int] = asyncio.Queue()
        for page_num in range(1, total_pages + 1):
            await queue.put(page_num)

        page_results: dict[int, str] = {}
        completed_count = 0
        progress_lock = asyncio.Lock()

        async def worker() -> None:
            nonlocal completed_count
            while not queue.empty():
                try:
                    page_num = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                hierarchy_hint = (
                    toc.get_active_hierarchy_for_page(page_num) if toc else "Documento Geral"
                )
                page_md = await self._transcribe_single_page(
                    raw_bytes=raw_bytes,
                    page_num=page_num,
                    total_pages=total_pages,
                    hierarchy_hint=hierarchy_hint,
                    effective_prompt=effective_prompt,
                    semaphore=self._semaphore,
                    kb_partition=kb_partition,
                    doc_id=doc_id,
                )
                page_results[page_num] = page_md
                queue.task_done()

                async with progress_lock:
                    completed_count += 1
                    cur = completed_count

                if progress_callback:
                    msg = f"Processando OCR: {cur}/{total_pages} páginas concluídas"
                    await progress_callback(cur, total_pages, msg)

        worker_count = min(self._max_concurrency, total_pages)
        workers = [asyncio.create_task(worker()) for _ in range(worker_count)]
        await asyncio.gather(*workers)

        # Concatenação e montagem final em ordem estritamente crescente
        output_blocks: list[str] = []
        for page_num in range(1, total_pages + 1):
            output_blocks.append(f"<!-- PAGE {page_num} -->\n{page_results.get(page_num, '')}")

        return "\n\n".join(output_blocks)
