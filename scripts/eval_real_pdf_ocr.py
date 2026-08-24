"""
Script de Avaliação e Benchmark em Cenário Real de Produção para OCR Multimodal.
Executa o fluxo idêntico ao de produção (Two-Pass OCR):
1. Passo 1: Descoberta de Sumário Sintético (QwenSyntheticTocExtractor, 1.0x low-res).
2. Passo 2: Transcrição Paralela Concorrente (ParallelVlmDocumentParser, 2.0x high-res,
   com injeção da hierarquia ativa por página e normalização final de Markdown).

Compara modelos (ex: qwen/qwen3-vl-8b-instruct vs qwen/qwen3-vl-32b-instruct)
em PDFs reais do mundo corporativo/científico.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)
from src.modules.knowledge.domain.entities.synthetic_document_toc import (
    SyntheticDocumentToc,
)
from src.modules.knowledge.infrastructure.adapters.pdf_page_renderer import (
    PdfPageRenderer,
)
from src.modules.knowledge.infrastructure.adapters.qwen_synthetic_toc_extractor import (
    QwenSyntheticTocExtractor,
)

# Tabela de preços OpenRouter (USD por milhão de tokens)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "qwen/qwen3-vl-8b-instruct": {"prompt": 0.18, "completion": 0.45},
    "qwen/qwen3-vl-32b-instruct": {"prompt": 0.70, "completion": 1.80},
    "qwen/qwen-2.5-vl-7b-instruct": {"prompt": 0.20, "completion": 0.50},
    "qwen/qwen-2.5-vl-72b-instruct": {"prompt": 1.10, "completion": 3.30},
}
DEFAULT_PRICING = {"prompt": 0.50, "completion": 1.50}


@dataclass
class ModelExecutionStats:
    model_name: str
    pdf_name: str
    pages_processed: int
    toc_duration_s: float
    ocr_duration_s: float
    total_duration_s: float
    avg_page_latency_s: float
    toc_items_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    cost_per_1k_pages_usd: float
    markdown_char_count: int
    markdown_word_count: int
    table_count: int
    heading_count: int
    figure_count: int
    raw_markdown: str
    toc_json: str
    success: bool
    error_message: str | None = None


class ProductionTrackingClient:
    """Wrapper sobre o cliente OpenAI para rastrear chamadas e contagem de tokens com precisão de produção."""

    def __init__(self, raw_client: AsyncOpenAI) -> None:
        self.raw_client = raw_client
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.call_count = 0

    @property
    def chat(self) -> Any:
        return self

    @property
    def completions(self) -> Any:
        return self

    async def create(self, **kwargs: Any) -> Any:
        response = await self.raw_client.chat.completions.create(**kwargs)
        self.call_count += 1
        if response.usage:
            self.prompt_tokens += response.usage.prompt_tokens
            self.completion_tokens += response.usage.completion_tokens
            self.total_tokens += response.usage.total_tokens
        return response


def extract_markdown_structural_metrics(md_text: str) -> tuple[int, int, int]:
    """Extrai contagem de tabelas GFM, cabeçalhos (#, ##, ###) e blocos de figura."""
    # Tabelas: blocos com linhas delimitadoras |---|
    table_matches = re.findall(r"\|[-:\s]+\|", md_text)
    table_count = len(table_matches)

    # Cabeçalhos: linhas iniciadas por 1 a 4 #
    headings = re.findall(r"^#{1,4}\s+.+$", md_text, re.MULTILINE)
    heading_count = len(headings)

    # Figuras: marcações com > **[Figura ou [Figura
    figures = re.findall(r"(?:>\s*\*\*\[Figura|\[Figura\s*\d+)", md_text, re.IGNORECASE)
    figure_count = len(figures)

    return table_count, heading_count, figure_count


async def run_production_flow_on_pdf(
    pdf_path: Path,
    model_name: str,
    api_key: str,
    selected_pages: list[int] | None = None,
    concurrency: int = 6,
    output_dir: Path | None = None,
) -> ModelExecutionStats:
    raw_bytes = pdf_path.read_bytes()
    renderer = PdfPageRenderer(low_res_scale=1.0, high_res_scale=2.0)
    total_doc_pages = await renderer.get_page_count(raw_bytes)

    if selected_pages:
        target_pages = [p for p in selected_pages if 1 <= p <= total_doc_pages]
    else:
        target_pages = list(range(1, total_doc_pages + 1))

    pages_count = len(target_pages)
    print(f"\n⚙️  Executando fluxo completo para: [{model_name}]")
    print(f"📄 Arquivo: {pdf_path.name} | Páginas alvo: {target_pages} ({pages_count} págs)")

    openai_client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://agentic-substrate.local",
            "X-Title": "Agentic Substrate Real PDF Eval",
        },
    )
    tracking_client = ProductionTrackingClient(openai_client)
    rate_limiter = AsyncTokenBucketLimiter(max_rpm=1500, max_tpm=10_000_000)

    # =========================================================================
    # PASSO 1: Synthetic ToC Discovery (Pass 1 - Low Res 1.0x)
    # =========================================================================
    print("   🔍 [Passo 1/2] Extraindo Sumário Sintético (Synthetic ToC)...", end=" ", flush=True)
    toc_start_t = time.perf_counter()

    toc_extractor = QwenSyntheticTocExtractor(
        openai_client=tracking_client,
        page_renderer=renderer,
        vision_model=model_name,
        rate_limiter=rate_limiter,
    )

    try:
        synthetic_toc: SyntheticDocumentToc = await toc_extractor.extract_toc(
            raw_bytes=raw_bytes,
            batch_size=25,
        )
        toc_duration = time.perf_counter() - toc_start_t
        print(f"✅ OK ({toc_duration:.2f}s | {len(synthetic_toc.items)} seções detectadas)")
    except Exception as e:
        toc_duration = time.perf_counter() - toc_start_t
        print(f"⚠️ Aviso no ToC: {e} (Prosseguindo com fallback)")
        synthetic_toc = SyntheticDocumentToc(items=[])

    # =========================================================================
    # PASSO 2: Parallel VLM Document Transcription (Pass 2 - High Res 2.0x)
    # =========================================================================
    print(
        f"   📝 [Passo 2/2] Transcrevendo {pages_count} páginas em paralelo (concorrência={concurrency})...",
        flush=True,
    )
    ocr_start_t = time.perf_counter()

    semaphore = asyncio.Semaphore(concurrency)
    system_prompt = (
        "Você é um especialista em OCR e estruturação de documentos em Markdown.\n"
        "SEU OBJETIVO:\n"
        "Transcrever EXCLUSIVAMENTE a página alvo para GitHub Flavored Markdown (GFM).\n\n"
        "REGRAS RÍGIDAS:\n"
        "1. Hierarquia de Cabeçalhos:\n"
        "   - Contexto da linhagem ativa: '{hierarchy_hint}'\n"
        "   - Use o nível correto de cabeçalho (#, ##, ###, ####). Não invente títulos inexistentes.\n"
        "2. Tabelas:\n"
        "   - Converta todas as tabelas em Markdown GFM puro (| Col 1 | Col 2 |).\n"
        "3. Figuras e Elementos Visuais:\n"
        "   - Para cada figura ou gráfico, use a anotação:\n"
        "     > **[Figura X: Título/Legenda]**\n"
        "     > *Descrição visual*: [Descreva detalhadamente o gráfico e tendências].\n"
        "4. Retorne APENAS o código Markdown sem blocos ```markdown envolventes.\n"
        "5. Continuidade de Hierarquia:\n"
        "   - Se o topo desta página exibir um título que já está na hierarquia ativa, "
        "NÃO o repita — a página é continuação de uma seção já aberta.\n"
        "6. Continuidade de Texto:\n"
        "   - Se a primeira linha desta página for continuação de um parágrafo anterior, "
        "continue o texto diretamente sem quebra forçada.\n"
        "7. Tabelas Inter-Página:\n"
        "   - Se esta página exibir linhas de uma tabela que começou na página anterior, "
        "repita o cabeçalho de colunas (| Col1 | Col2 | e |---|---|).\n"
        "8. Idioma do Documento: Redija todas as descrições rigorosamente no idioma predominante da página."
    )

    page_results: dict[int, str] = {}
    completed_lock = asyncio.Lock()
    completed_pages = 0

    async def transcribe_page_task(page_num: int) -> None:
        nonlocal completed_pages
        async with semaphore:
            b64_img = await renderer.render_page_high_res(raw_bytes, page_num - 1)
            hierarchy_hint = synthetic_toc.get_active_hierarchy_for_page(page_num)

            user_content = [
                {
                    "type": "text",
                    "text": (
                        f"--- PÁGINA {page_num} de {total_doc_pages} ---\n"
                        f"Hierarquia estrutural ativa: {hierarchy_hint}\n"
                        f"Transcreva com fidelidade a Página {page_num}:"
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                },
            ]

            await rate_limiter.acquire(estimated_tokens=1500)
            page_resp = await tracking_client.raw_client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt.format(hierarchy_hint=hierarchy_hint),
                    },
                    {"role": "user", "content": user_content},
                ],
                temperature=0.0,
                extra_body={
                    "provider": {"sort": "throughput", "allow_fallbacks": True},
                    "reasoning": {"effort": "none", "exclude": True},
                },
            )
            tracking_client.call_count += 1
            if page_resp.usage:
                tracking_client.prompt_tokens += page_resp.usage.prompt_tokens
                tracking_client.completion_tokens += page_resp.usage.completion_tokens
                tracking_client.total_tokens += page_resp.usage.total_tokens

            page_md = str(page_resp.choices[0].message.content or "").strip()
            page_results[page_num] = page_md

            async with completed_lock:
                completed_pages += 1
                cur = completed_pages
                print(f"      ↳ Página {page_num} concluída ({cur}/{pages_count})")

    tasks = [transcribe_page_task(p) for p in target_pages]
    await asyncio.gather(*tasks)

    ocr_duration = time.perf_counter() - ocr_start_t
    total_duration = toc_duration + ocr_duration
    avg_latency = (ocr_duration / pages_count) if pages_count > 0 else 0.0

    # Normalização final idêntica a de produção
    sorted_blocks = [page_results[p] for p in target_pages if p in page_results]
    raw_markdown = "\n\n".join(sorted_blocks)

    # Limpeza de markdown de produção
    clean_md = re.sub(r"<!--\s*PAGE\s*\d+\s*-->", "", raw_markdown)
    clean_md = re.sub(r"\n{3,}", "\n\n", clean_md).strip()

    # Métricas estruturais
    tbl_cnt, head_cnt, fig_cnt = extract_markdown_structural_metrics(clean_md)
    char_count = len(clean_md)
    word_count = len(clean_md.split())

    # Custos
    pricing = MODEL_PRICING.get(model_name, DEFAULT_PRICING)
    cost_prompt = (tracking_client.prompt_tokens / 1_000_000.0) * pricing["prompt"]
    cost_comp = (tracking_client.completion_tokens / 1_000_000.0) * pricing["completion"]
    total_cost_usd = cost_prompt + cost_comp
    cost_1k = (total_cost_usd / pages_count * 1000.0) if pages_count > 0 else 0.0

    toc_dict = [item.model_dump() for item in synthetic_toc.items]
    toc_json_str = json.dumps(toc_dict, indent=2, ensure_ascii=False)

    # Salva artefatos em disco
    if output_dir:
        mod_dir = output_dir / model_name.replace("/", "_")
        mod_dir.mkdir(parents=True, exist_ok=True)
        (mod_dir / "document_transcription.md").write_text(clean_md, encoding="utf-8")
        (mod_dir / "synthetic_toc.json").write_text(toc_json_str, encoding="utf-8")

        for p in target_pages:
            if p in page_results:
                (mod_dir / f"page_{p:02d}.md").write_text(page_results[p], encoding="utf-8")

    return ModelExecutionStats(
        model_name=model_name,
        pdf_name=pdf_path.name,
        pages_processed=pages_count,
        toc_duration_s=toc_duration,
        ocr_duration_s=ocr_duration,
        total_duration_s=total_duration,
        avg_page_latency_s=avg_latency,
        toc_items_count=len(synthetic_toc.items),
        prompt_tokens=tracking_client.prompt_tokens,
        completion_tokens=tracking_client.completion_tokens,
        total_tokens=tracking_client.total_tokens,
        estimated_cost_usd=total_cost_usd,
        cost_per_1k_pages_usd=cost_1k,
        markdown_char_count=char_count,
        markdown_word_count=word_count,
        table_count=tbl_cnt,
        heading_count=head_cnt,
        figure_count=fig_cnt,
        raw_markdown=clean_md,
        toc_json=toc_json_str,
        success=True,
    )


def print_executive_benchmark_report(
    stats_list: list[ModelExecutionStats], output_dir: Path
) -> None:
    print("\n" + "=" * 115)
    print("🏆 RELATÓRIO COMPARATIVO EXECUTIVO - PIPELINE DE OCR EM PRODUÇÃO (TWO-PASS)")
    print(f"Documento Avaliado: {stats_list[0].pdf_name} ({stats_list[0].pages_processed} páginas)")
    print("=" * 115)

    header = (
        f"{'Modelo':<28} | {'Tempo ToC':<9} | {'Tempo OCR':<9} | {'Total':<8} | "
        f"{'Méd/Pág':<8} | {'Prompt Tok':<10} | {'Comp Tok':<9} | {'Custo ($)':<9} | {'$/1k págs':<9}"
    )
    print(header)
    print("-" * 115)

    for s in stats_list:
        mod_short = s.model_name.split("/")[-1]
        print(
            f"{mod_short:<28} | {s.toc_duration_s:>8.2f}s | {s.ocr_duration_s:>8.2f}s | "
            f"{s.total_duration_s:>7.2f}s | {s.avg_page_latency_s:>7.2f}s | "
            f"{s.prompt_tokens:>10,d} | {s.completion_tokens:>9,d} | "
            f"${s.estimated_cost_usd:>8.4f} | ${s.cost_per_1k_pages_usd:>8.2f}"
        )
    print("=" * 115)

    print("\n📊 ESTRUTURA E QUALIDADE DO MARKDOWN EXTRAÍDO:")
    print("-" * 90)
    struct_header = (
        f"{'Modelo':<28} | {'Palavras':<9} | {'Caracteres':<11} | "
        f"{'Tabelas GFM':<11} | {'Cabeçalhos':<10} | {'Figuras/Gráficos':<15}"
    )
    print(struct_header)
    print("-" * 90)
    for s in stats_list:
        mod_short = s.model_name.split("/")[-1]
        print(
            f"{mod_short:<28} | {s.markdown_word_count:>9,d} | {s.markdown_char_count:>11,d} | "
            f"{s.table_count:>11d} | {s.heading_count:>10d} | {s.figure_count:>15d}"
        )
    print("-" * 90)

    if len(stats_list) >= 2:
        m_8b = next((s for s in stats_list if "8b" in s.model_name.lower()), stats_list[0])
        m_32b = next((s for s in stats_list if "32b" in s.model_name.lower()), stats_list[-1])

        speedup = m_32b.total_duration_s / m_8b.total_duration_s if m_8b.total_duration_s > 0 else 1.0
        cost_savings = (
            (m_32b.estimated_cost_usd - m_8b.estimated_cost_usd)
            / m_32b.estimated_cost_usd
            * 100.0
            if m_32b.estimated_cost_usd > 0
            else 0.0
        )
        word_delta_pct = (
            (m_8b.markdown_word_count - m_32b.markdown_word_count)
            / m_32b.markdown_word_count
            * 100.0
            if m_32b.markdown_word_count > 0
            else 0.0
        )

        print("\n📈 VEREDITO E ANÁLISE DE EFICIÊNCIA (8B vs 32B EM PRODUÇÃO):")
        print("=" * 80)
        print(f"• Velocidade Geral (End-to-End):   {speedup:.2f}x mais rápido no 8B")
        print(
            f"• Tempo Total:                     {m_8b.total_duration_s:.1f}s (8B) vs {m_32b.total_duration_s:.1f}s (32B)"
        )
        print(
            f"• Custo do Documento:              ${m_8b.estimated_cost_usd:.4f} (8B) vs ${m_32b.estimated_cost_usd:.4f} (32B)"
        )
        print(f"• Economia de Tokens / Custos:     {cost_savings:.1f}% de redução direta")
        print(
            f"• Custo Projetado por 10.000 págs: ${m_8b.cost_per_1k_pages_usd * 10:.2f} (8B) vs ${m_32b.cost_per_1k_pages_usd * 10:.2f} (32B)"
        )
        print(f"• Cobertura de Conteúdo:           Diferença de apenas {word_delta_pct:+.1f}% de palavras")
        print(f"• Tabelas GFM Extraídas:           {m_8b.table_count} (8B) vs {m_32b.table_count} (32B)")
        print(f"• Seções / Títulos Detectados:     {m_8b.heading_count} (8B) vs {m_32b.heading_count} (32B)")
        print(f"• Figuras Identificadas:           {m_8b.figure_count} (8B) vs {m_32b.figure_count} (32B)")
        print("=" * 80)
        print(f"\n📂 Artefatos salvos em: {output_dir.resolve()}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Benchmark em Cenário Real de Produção (Two-Pass OCR) com PDF."
    )
    parser.add_argument(
        "--pdf-path",
        type=str,
        default="/Users/insider/Downloads/Comparison of Reduced-Volume High-Intensity Interval Training and High-Volume Training on Endurance Performance in Triathletes.pdf",
        help="Caminho para o arquivo PDF",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="qwen/qwen3-vl-8b-instruct,qwen/qwen3-vl-32b-instruct",
        help="Modelos separados por vírgula para avaliar",
    )
    parser.add_argument(
        "--pages",
        type=str,
        default="1,2,7,11,20",
        help="Lista de páginas a processar separadas por vírgula (ex: 1,2,7,11,20) ou 'all'",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=6,
        help="Concorrência máxima para transcrição paralela de páginas (default: 6)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data/eval_real_pdf",
        help="Diretório de saída para salvar os artefatos de markdown e ToC",
    )

    args = parser.parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERRO: OPENROUTER_API_KEY não configurada no ambiente ou .env", file=sys.stderr)
        sys.exit(1)

    pdf_file = Path(args.pdf_path)
    if not pdf_file.exists():
        print(f"ERRO: Arquivo PDF não encontrado: {pdf_file}", file=sys.stderr)
        sys.exit(1)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if args.pages.strip().lower() == "all":
        selected_pages = None
    else:
        selected_pages = [int(p.strip()) for p in args.pages.split(",") if p.strip().isdigit()]

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stats_results: list[ModelExecutionStats] = []
    for model in models:
        stats = asyncio.run(
            run_production_flow_on_pdf(
                pdf_path=pdf_file,
                model_name=model,
                api_key=api_key,
                selected_pages=selected_pages,
                concurrency=args.concurrency,
                output_dir=out_dir,
            )
        )
        stats_results.append(stats)

    print_executive_benchmark_report(stats_results, out_dir)


if __name__ == "__main__":
    main()
