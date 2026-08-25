import json
import re
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)
from src.modules.knowledge.domain.entities.synthetic_document_toc import (
    SyntheticDocumentToc,
)
from src.modules.knowledge.domain.interfaces.i_synthetic_toc_extractor import (
    ISyntheticTocExtractor,
)
from src.modules.knowledge.domain.value_objects.hierarchical_toc_item import (
    HierarchicalTocItem,
)
from src.modules.knowledge.domain.value_objects.toc_batch_state import (
    TocBatchState,
)
from src.modules.knowledge.infrastructure.adapters.openrouter_provider_defaults import (
    OpenRouterProviderDefaults,
)
from src.modules.knowledge.infrastructure.adapters.pdf_page_renderer import (
    PdfPageRenderer,
)
from src.modules.knowledge.infrastructure.adapters.toc_checkpoint_storage import (
    TocCheckpointStorage,
)


class QwenSyntheticTocExtractor(ISyntheticTocExtractor):
    """
    Extrator de Sumário Sintético (Synthetic ToC) via Qwen-VL / OpenRouter.
    Executa o fatiamento em lotes encadeados com passagem de estado hierárquico
    (Stateful Rolling Window) e persistência atômica de checkpoints por lote
    para garantir desperdício zero de tokens em caso de reinicialização da saga.
    """

    def __init__(
        self,
        openai_client: Any,
        page_renderer: PdfPageRenderer | None = None,
        vision_model: str = "qwen/qwen3-vl-32b-instruct",
        rate_limiter: AsyncTokenBucketLimiter | None = None,
        checkpoint_storage: TocCheckpointStorage | None = None,
    ) -> None:
        self._client = openai_client
        self._renderer = page_renderer or PdfPageRenderer()
        self._vision_model = vision_model
        self._limiter = rate_limiter
        self._checkpoint_storage = checkpoint_storage

    def _parse_json_items(self, raw_text: str) -> list[dict[str, Any]]:
        """Extrai de forma resiliente a lista de nós JSON a partir do texto do LLM."""
        text = raw_text.strip()
        # Remove blocos markdown ```json ... ``` se presentes
        if "```" in text:
            match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
            if match:
                text = match.group(1)
            else:
                # Tenta capturar array bruto dentro do texto
                match_arr = re.search(r"(\[[\s\S]*\])", text)
                if match_arr:
                    text = match_arr.group(1)

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except Exception:
            pass
        return []

    async def extract_toc(
        self,
        raw_bytes: bytes,
        batch_size: int = 25,
        progress_callback: (Callable[[int, int, str], Coroutine[Any, Any, None]] | None) = None,
        doc_id: UUID | None = None,
        kb_partition: str | None = None,
    ) -> SyntheticDocumentToc:
        total_pages = await self._renderer.get_page_count(raw_bytes)
        if total_pages <= 0:
            return SyntheticDocumentToc(items=[])

        effective_batch_size = max(1, batch_size)
        total_batches = (total_pages + effective_batch_size - 1) // effective_batch_size

        # 1. Fast-Path: Verifica se o ToC consolidado completo já existe em cache
        if self._checkpoint_storage and kb_partition and doc_id:
            if await self._checkpoint_storage.has_toc(kb_partition, doc_id):
                cached_toc = await self._checkpoint_storage.get_toc(kb_partition, doc_id)
                if cached_toc is not None:
                    if progress_callback:
                        msg = "Sumário Sintético recuperado integralmente do cache (0 tokens)"
                        await progress_callback(total_batches, total_batches, msg)
                    return cached_toc

        all_toc_items: list[HierarchicalTocItem] = []
        current_state = TocBatchState.initial()
        batch_count = 0

        for start_idx in range(0, total_pages, effective_batch_size):
            batch_count += 1
            end_idx = min(start_idx + effective_batch_size, total_pages)
            batch_page_count = end_idx - start_idx

            # 2. Verifica se o lote atual já existe no checkpoint de disco
            if self._checkpoint_storage and kb_partition and doc_id:
                if await self._checkpoint_storage.has_batch(kb_partition, doc_id, batch_count):
                    cached_batch = await self._checkpoint_storage.get_batch(
                        kb_partition, doc_id, batch_count
                    )
                    if cached_batch is not None:
                        batch_items, restored_state = cached_batch
                        all_toc_items.extend(batch_items)
                        current_state = restored_state

                        if progress_callback:
                            msg = (
                                f"Extraindo Sumário Sintético: Lote {batch_count}/{total_batches} "
                                f"(Págs {start_idx + 1}-{end_idx}) (Reutilizado do Cache)"
                            )
                            await progress_callback(batch_count, total_batches, msg)
                        continue

            if progress_callback:
                msg = (
                    f"Extraindo Sumário Sintético: Lote {batch_count}/{total_batches} "
                    f"(Págs {start_idx + 1}-{end_idx})"
                )
                await progress_callback(batch_count, total_batches, msg)

            content_payload: list[dict[str, Any]] = []
            context_hint = current_state.to_prompt_context()

            content_payload.append(
                {
                    "type": "text",
                    "text": (
                        f"Documento com {total_pages} páginas no total. "
                        f"Analisando agora o lote das Páginas {start_idx + 1} até {end_idx}.\n"
                        f"{context_hint}\n"
                        "Analise as imagens abaixo e gere a Árvore de Seções deste lote."
                    ),
                }
            )

            # Renderiza as páginas do lote atual em baixa resolução (1.0x)
            for page_num in range(start_idx + 1, end_idx + 1):
                b64_img = await self._renderer.render_page_low_res(raw_bytes, page_num - 1)
                content_payload.append(
                    {
                        "type": "text",
                        "text": f"[PÁGINA {page_num}]",
                    }
                )
                content_payload.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                    }
                )

            system_prompt = (
                "Você é um especialista em análise estrutural de documentos.\n"
                "SEU OBJETIVO: Identificar a árvore de títulos e seções (Synthetic ToC) "
                "deste lote de páginas.\n\n"
                "REGRAS:\n"
                "1. Extraia apenas títulos reais (# Título Principal, ## Seção, ### Subseção).\n"
                "2. Para subseções, preencha parent_section com o título da seção pai.\n"
                "3. Responda ESTRITAMENTE em formato JSON com uma lista de objetos:\n"
                "[\n"
                '  {"type": "document_title"|"section"|"subsection", '
                '"markdown_level": "#"|"##"|"###", '
                '"title": "...", "page": N, "parent_section": "..."|null}\n'
                "]"
            )

            if self._limiter:
                # Estimativa de tokens para a chamada
                await self._limiter.acquire(estimated_tokens=500 * batch_page_count)

            response = await self._client.chat.completions.create(
                model=self._vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_payload},
                ],
                temperature=0.0,
                extra_body=OpenRouterProviderDefaults.get_throughput_extra_body(),
            )

            raw_response = response.choices[0].message.content or ""
            items_raw = self._parse_json_items(raw_response)
            batch_toc_items: list[HierarchicalTocItem] = []

            for item_dict in items_raw:
                try:
                    # Garante que page seja inteiro dentro do range
                    raw_page = int(item_dict.get("page", start_idx + 1))
                    page_val = max(start_idx + 1, min(raw_page, end_idx))
                    raw_type = item_dict.get("type", "section")
                    valid_types = ("document_title", "section", "subsection", "sub_subsection")
                    item_type = raw_type if raw_type in valid_types else "section"
                    level = item_dict.get("markdown_level", "##")
                    title = str(item_dict.get("title", "")).strip()

                    if not title or level not in ("#", "##", "###", "####"):
                        continue

                    toc_item = HierarchicalTocItem.model_validate(
                        {
                            "type": item_type,
                            "markdown_level": level,
                            "title": title,
                            "page": page_val,
                            "parent_section": item_dict.get("parent_section"),
                        }
                    )
                    all_toc_items.append(toc_item)
                    batch_toc_items.append(toc_item)

                    # Atualiza o estado ativo para o próximo lote
                    if level == "##":
                        current_state = TocBatchState(
                            active_section=title,
                            active_subsection=None,
                            active_markdown_level="##",
                            last_page_processed=end_idx,
                        )
                    elif level == "###":
                        current_state = TocBatchState(
                            active_section=current_state.active_section,
                            active_subsection=title,
                            active_markdown_level="###",
                            last_page_processed=end_idx,
                        )
                except Exception:
                    continue

            # Se nenhum heading foi encontrado neste lote, preserva a seção anterior
            current_state = TocBatchState(
                active_section=current_state.active_section,
                active_subsection=current_state.active_subsection,
                active_markdown_level=current_state.active_markdown_level,
                last_page_processed=end_idx,
            )

            # Persiste checkpoint do lote no disco/storage
            if self._checkpoint_storage and kb_partition and doc_id:
                await self._checkpoint_storage.save_batch(
                    kb_partition, doc_id, batch_count, batch_toc_items, current_state
                )

        final_toc = SyntheticDocumentToc(items=all_toc_items)
        if self._checkpoint_storage and kb_partition and doc_id:
            await self._checkpoint_storage.save_toc(kb_partition, doc_id, final_toc)

        return final_toc
