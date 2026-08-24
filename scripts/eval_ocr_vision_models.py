"""
Script de Avaliação e Benchmark de Modelos de Visão Multimodal para OCR.
Compara modelos (ex: qwen/qwen3-vl-8b-instruct vs qwen/qwen3-vl-32b-instruct)
em múltiplos cenários: tabelas financeiras densas, hierarquias de cabeçalhos,
gráficos/diagramas visuais e documentos PDF reais.

Mede:
- Latência por página (ms) e vazão (throughput em tokens/s)
- Consumo de tokens (Prompt, Completion, Total)
- Custo operacional estimado ($ por página e por 1.000 páginas)
- Qualidade estrutural: Preservação de tabelas GFM, hierarquia de cabeçalhos,
  anotação multimodal de figuras e revocação de palavras-chave críticas.
"""

import argparse
import asyncio
import base64
import io
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFont

from src.modules.knowledge.infrastructure.adapters.pdf_page_renderer import (
    PdfPageRenderer,
)

# Preços de referência OpenRouter (USD por milhão de tokens)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "qwen/qwen3-vl-8b-instruct": {"prompt": 0.18, "completion": 0.45},
    "qwen/qwen3-vl-32b-instruct": {"prompt": 0.70, "completion": 1.80},
    "qwen/qwen-2.5-vl-7b-instruct": {"prompt": 0.20, "completion": 0.50},
    "qwen/qwen-2.5-vl-72b-instruct": {"prompt": 1.10, "completion": 3.30},
    "google/gemini-2.5-flash": {"prompt": 0.15, "completion": 0.60},
}
DEFAULT_PRICING = {"prompt": 0.50, "completion": 1.50}


@dataclass
class GroundTruthScenario:
    name: str
    description: str
    image_bytes: bytes  # JPEG bytes
    expected_headings: list[str] = field(default_factory=list)
    expected_table_columns: list[str] = field(default_factory=list)
    expected_keywords: list[str] = field(default_factory=list)
    has_figure: bool = False
    expected_figure_legend: str | None = None


@dataclass
class OcrEvalResult:
    model_name: str
    scenario_name: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    cost_per_1k_pages_usd: float
    table_score_pct: float
    heading_score_pct: float
    keyword_recall_pct: float
    figure_score_pct: float
    overall_quality_pct: float
    success: bool
    markdown_output: str
    error_message: str | None = None


def get_default_font(size: int = 16) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def generate_synthetic_table_scenario() -> GroundTruthScenario:
    """Cenário 1: Relatório Financeiro com Tabela Densa e Múltiplas Colunas."""
    img = Image.new("RGB", (1200, 1500), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    # Título Principal
    d.text((80, 60), "Demonstrativo de Resultados do Exercício (DRE)", fill=(0, 0, 0))
    d.text((80, 95), "Relatório Corporativo Consolidado - Exercício 2025/2026", fill=(80, 80, 80))
    d.line([(80, 130), (1120, 130)], fill=(0, 0, 0), width=2)

    # Introdução
    d.text(
        (80, 155),
        "Apresentamos abaixo a performance operacional trimestral da companhia.",
        fill=(30, 30, 30),
    )

    # Tabela com bordas
    table_x, table_y = 80, 210
    col_widths = [180, 200, 180, 200, 200]
    row_height = 45

    # Cabeçalho da Tabela
    headers = [
        "Trimestre",
        "Receita Líquida (R$)",
        "Margem Bruta (%)",
        "EBITDA (R$)",
        "Lucro Líquido (R$)",
    ]
    cur_x = table_x
    for i, h in enumerate(headers):
        d.rectangle(
            [cur_x, table_y, cur_x + col_widths[i], table_y + row_height],
            fill=(230, 235, 245),
            outline=(100, 100, 100),
            width=1,
        )
        d.text((cur_x + 10, table_y + 12), h, fill=(0, 0, 0))
        cur_x += col_widths[i]

    # Linhas da Tabela
    rows = [
        ["1T2025", "R$ 4.250.000,00", "34,8%", "R$ 1.120.000,00", "R$ 780.000,00"],
        ["2T2025", "R$ 4.890.000,00", "36,2%", "R$ 1.340.000,00", "R$ 920.000,00"],
        ["3T2025", "R$ 5.150.000,00", "35,5%", "R$ 1.410.000,00", "R$ 985.000,00"],
        ["4T2025", "R$ 6.300.000,00", "38,1%", "R$ 1.850.000,00", "R$ 1.350.000,00"],
        ["Total Anual", "R$ 20.590.000,00", "36,3%", "R$ 5.720.000,00", "R$ 4.035.000,00"],
    ]

    for r_idx, row_data in enumerate(rows):
        cur_y = table_y + (r_idx + 1) * row_height
        cur_x = table_x
        bg = (248, 248, 250) if r_idx % 2 == 1 else (255, 255, 255)
        if r_idx == len(rows) - 1:
            bg = (225, 230, 240)

        for c_idx, val in enumerate(row_data):
            d.rectangle(
                [cur_x, cur_y, cur_x + col_widths[c_idx], cur_y + row_height],
                fill=bg,
                outline=(120, 120, 120),
                width=1,
            )
            d.text((cur_x + 10, cur_y + 12), val, fill=(0, 0, 0))
            cur_x += col_widths[c_idx]

    # Notas explicativas
    notes_y = table_y + len(rows) * row_height + 80
    d.text(
        (80, notes_y),
        "Nota Explicativa 1: Os valores foram auditados e cumprem as normas IFRS.",
        fill=(50, 50, 50),
    )
    d.text(
        (80, notes_y + 30),
        "Nota Explicativa 2: O crescimento do 4T2025 decorreu de sazonalidade positiva.",
        fill=(50, 50, 50),
    )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return GroundTruthScenario(
        name="Tabela_Financeira_Densa",
        description="Página com demonstrativo de resultados contábil, 5 colunas e 5 linhas.",
        image_bytes=buf.getvalue(),
        expected_headings=["Demonstrativo de Resultados do Exercício (DRE)"],
        expected_table_columns=[
            "Trimestre",
            "Receita Líquida",
            "Margem Bruta",
            "EBITDA",
            "Lucro Líquido",
        ],
        expected_keywords=[
            "4.250.000",
            "34,8%",
            "20.590.000",
            "1.850.000",
            "Total Anual",
            "IFRS",
            "Nota Explicativa 1",
        ],
        has_figure=False,
    )


def generate_synthetic_hierarchy_scenario() -> GroundTruthScenario:
    """Cenário 2: Documento com Múltiplos Níveis de Títulos, Subtítulos e Listas."""
    img = Image.new("RGB", (1200, 1500), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    y = 60
    # H1
    d.text((80, y), "Manual de Governança e Diretrizes Corporativas", fill=(0, 0, 0))
    d.line([(80, y + 35), (1120, y + 35)], fill=(0, 0, 0), width=2)
    y += 65

    # Parágrafo
    d.text(
        (80, y),
        "Este manual estabelece as normas éticas e operacionais a serem seguidas por todos os colaboradores.",
        fill=(40, 40, 40),
    )
    y += 45

    # H2
    d.text((80, y), "Capítulo I - Princípios Fundamentais", fill=(0, 0, 0))
    d.line([(80, y + 30), (700, y + 30)], fill=(80, 80, 80), width=1)
    y += 50

    # H3
    d.text((80, y), "Artigo 1º - Transparência e Integridade", fill=(0, 0, 0))
    y += 35
    d.text(
        (80, y),
        "Todas as transações comerciais e comunicações oficiais devem refletir a verdade estrita dos fatos.",
        fill=(40, 40, 40),
    )
    y += 45

    # Lista
    items = [
        "1. Registro contábil fidedigno sem qualquer omissão deliberada.",
        "2. Proteção irrestrita de dados sigilosos e conformidade com a LGPD.",
        "3. Proibição absoluta de conflito de interesses em negociações com fornecedores.",
    ]
    for item in items:
        d.text((110, y), item, fill=(30, 30, 30))
        y += 35
    y += 20

    # H2
    d.text((80, y), "Capítulo II - Segurança da Informação e Conformidade", fill=(0, 0, 0))
    d.line([(80, y + 30), (700, y + 30)], fill=(80, 80, 80), width=1)
    y += 50

    # H3
    d.text((80, y), "Artigo 2º - Gestão de Acessos e Senhas", fill=(0, 0, 0))
    y += 35
    d.text(
        (80, y),
        "As credenciais de acesso são individuais, intransferíveis e protegidas por autenticação MFA obrigatória.",
        fill=(40, 40, 40),
    )
    y += 45

    sub_items = [
        "- Uso de senhas com comprimento mínimo de 14 caracteres alfanuméricos.",
        "- Rotação periódica de credenciais a cada 90 dias úteis.",
        "- Bloqueio automático de estações de trabalho após 5 minutos de inatividade.",
    ]
    for s in sub_items:
        d.text((110, y), s, fill=(30, 30, 30))
        y += 35

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return GroundTruthScenario(
        name="Hierarquia_Estrutural_Normativa",
        description="Página com cabeçalhos H1, H2, H3, artigos legais e listas numeradas/bullets.",
        image_bytes=buf.getvalue(),
        expected_headings=[
            "Manual de Governança e Diretrizes Corporativas",
            "Capítulo I - Princípios Fundamentais",
            "Artigo 1º - Transparência e Integridade",
            "Capítulo II - Segurança da Informação e Conformidade",
            "Artigo 2º - Gestão de Acessos e Senhas",
        ],
        expected_keywords=[
            "LGPD",
            "conflito de interesses",
            "autenticação MFA",
            "14 caracteres",
            "90 dias",
            "5 minutos",
        ],
        has_figure=False,
    )


def generate_synthetic_chart_scenario() -> GroundTruthScenario:
    """Cenário 3: Página com Gráfico Visual de Barras, Eixos e Legenda."""
    img = Image.new("RGB", (1200, 1500), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    y = 60
    d.text((80, y), "Relatório Executivo de Infraestrutura Cloud", fill=(0, 0, 0))
    y += 45
    d.text(
        (80, y),
        "Abaixo destacamos a evolução dos custos mensais por provedor no último trimestre.",
        fill=(40, 40, 40),
    )
    y += 70

    # Desenhar Gráfico de Barras
    chart_x, chart_y = 120, y
    chart_w, chart_h = 900, 400

    # Eixos
    d.line(
        [(chart_x, chart_y + chart_h), (chart_x + chart_w, chart_y + chart_h)],
        fill=(0, 0, 0),
        width=2,
    )
    d.line([(chart_x, chart_y), (chart_x, chart_y + chart_h)], fill=(0, 0, 0), width=2)

    # Grid lines horizontais
    for step in range(1, 5):
        gy = chart_y + chart_h - (step * 80)
        d.line([(chart_x, gy), (chart_x + chart_w, gy)], fill=(220, 220, 220), width=1)
        val_str = f"R$ {step * 25}k"
        d.text((chart_x - 70, gy - 8), val_str, fill=(80, 80, 80))

    # Barras do Gráfico
    bars = [
        ("Jan/2026 - AWS", 180, (65, 105, 225), "R$ 45k"),
        ("Jan/2026 - GCP", 240, (50, 150, 50), "R$ 60k"),
        ("Fev/2026 - AWS", 210, (65, 105, 225), "R$ 52k"),
        ("Fev/2026 - GCP", 300, (50, 150, 50), "R$ 75k"),
        ("Mar/2026 - AWS", 260, (65, 105, 225), "R$ 65k"),
        ("Mar/2026 - GCP", 360, (50, 150, 50), "R$ 90k"),
    ]

    bar_width = 75
    spacing = 55
    start_bar_x = chart_x + 60

    for idx, (label, h_val, color, text_val) in enumerate(bars):
        bx = start_bar_x + idx * (bar_width + spacing)
        by = chart_y + chart_h - h_val
        d.rectangle([bx, by, bx + bar_width, chart_y + chart_h], fill=color, outline=(0, 0, 0))
        d.text((bx + 10, by - 22), text_val, fill=(0, 0, 0))
        d.text((bx - 10, chart_y + chart_h + 15), label, fill=(50, 50, 50))

    # Legenda da Figura
    fig_y = chart_y + chart_h + 80
    d.rectangle(
        [chart_x, fig_y, chart_x + chart_w, fig_y + 80],
        fill=(245, 247, 250),
        outline=(180, 180, 180),
    )
    d.text(
        (chart_x + 20, fig_y + 15),
        "Figura 1: Evolução Comparativa de Gastos Mensais em Infraestrutura Cloud (AWS vs GCP)",
        fill=(0, 0, 0),
    )
    d.text(
        (chart_x + 20, fig_y + 45),
        "Fonte: Controladoria Interna de Engenharia e Finanças.",
        fill=(100, 100, 100),
    )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return GroundTruthScenario(
        name="Grafico_Visual_Multimodal",
        description="Página com gráfico de barras de gastos cloud e anotação formal de Figura 1.",
        image_bytes=buf.getvalue(),
        expected_headings=["Relatório Executivo de Infraestrutura Cloud"],
        expected_keywords=["AWS", "GCP", "Jan/2026", "Mar/2026", "R$ 90k", "Controladoria"],
        has_figure=True,
        expected_figure_legend="Figura 1: Evolução Comparativa de Gastos Mensais",
    )


def compute_metrics(
    output_md: str,
    scenario: GroundTruthScenario,
    latency_ms: float,
    prompt_tokens: int,
    completion_tokens: int,
    model_name: str,
) -> OcrEvalResult:
    # 1. Avaliação de Tabelas
    table_score = 100.0
    if scenario.expected_table_columns:
        has_pipe_rows = len(re.findall(r"\|.*\|", output_md)) >= 3
        has_delimiter = bool(re.search(r"\|[-:\s]+\|", output_md))
        cols_found = sum(
            1
            for col in scenario.expected_table_columns
            if col.lower() in output_md.lower()
        )
        col_ratio = cols_found / len(scenario.expected_table_columns)
        if not (has_pipe_rows and has_delimiter):
            table_score = col_ratio * 40.0
        else:
            table_score = 50.0 + (col_ratio * 50.0)

    # 2. Avaliação de Cabeçalhos
    heading_score = 100.0
    if scenario.expected_headings:
        headings_found = 0
        for h in scenario.expected_headings:
            if h.lower() in output_md.lower():
                headings_found += 1
        heading_score = (headings_found / len(scenario.expected_headings)) * 100.0

    # 3. Avaliação de Palavras-Chave / Valores Críticos
    keyword_score = 100.0
    if scenario.expected_keywords:
        kw_found = sum(
            1 for kw in scenario.expected_keywords if kw.lower() in output_md.lower()
        )
        keyword_score = (kw_found / len(scenario.expected_keywords)) * 100.0

    # 4. Avaliação de Anotação de Figura
    figure_score = 100.0
    if scenario.has_figure:
        has_fig_tag = bool(
            re.search(r">\s*\*\*\[Figura", output_md, re.IGNORECASE)
            or re.search(r"\[Figura\s*\d+", output_md, re.IGNORECASE)
        )
        has_desc_tag = bool(
            re.search(r"descri[cç][aã]o\s*visual", output_md, re.IGNORECASE)
        )
        fig_pts = (50.0 if has_fig_tag else 0.0) + (50.0 if has_desc_tag else 0.0)
        figure_score = fig_pts

    # 5. Cálculo do Score Geral Ponderado
    weights = []
    scores = []
    if scenario.expected_table_columns:
        weights.append(0.35)
        scores.append(table_score)
    if scenario.expected_headings:
        weights.append(0.25)
        scores.append(heading_score)
    if scenario.expected_keywords:
        weights.append(0.25)
        scores.append(keyword_score)
    if scenario.has_figure:
        weights.append(0.35)
        scores.append(figure_score)

    if not weights:
        overall_quality = 100.0
    else:
        overall_quality = sum(s * w for s, w in zip(scores, weights)) / sum(weights)

    # 6. Cálculo de Custo Estimado
    pricing = MODEL_PRICING.get(model_name, DEFAULT_PRICING)
    cost_prompt = (prompt_tokens / 1_000_000.0) * pricing["prompt"]
    cost_comp = (completion_tokens / 1_000_000.0) * pricing["completion"]
    cost_usd = cost_prompt + cost_comp
    cost_1k = cost_usd * 1000.0

    return OcrEvalResult(
        model_name=model_name,
        scenario_name=scenario.name,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=cost_usd,
        cost_per_1k_pages_usd=cost_1k,
        table_score_pct=table_score,
        heading_score_pct=heading_score,
        keyword_recall_pct=keyword_score,
        figure_score_pct=figure_score,
        overall_quality_pct=overall_quality,
        success=True,
        markdown_output=output_md,
    )


async def execute_ocr_call(
    client: AsyncOpenAI | None,
    model_name: str,
    image_bytes: bytes,
    prompt_instructions: str | None = None,
    dry_run: bool = False,
) -> tuple[str, float, int, int]:
    """Executa a chamada multimodal ao modelo de visão e retorna (markdown, latency_ms, prompt_tok, comp_tok)."""
    b64_img = base64.b64encode(image_bytes).decode("utf-8")

    if dry_run or client is None:
        await asyncio.sleep(0.2)
        mock_output = (
            "# Demonstrativo de Resultados do Exercício (DRE)\n\n"
            "| Trimestre | Receita Líquida (R$) | Margem Bruta (%) | EBITDA (R$) | Lucro Líquido (R$) |\n"
            "|---|---|---|---|---|\n"
            "| 1T2025 | R$ 4.250.000,00 | 34,8% | R$ 1.120.000,00 | R$ 780.000,00 |\n"
            "| 4T2025 | R$ 6.300.000,00 | 38,1% | R$ 1.850.000,00 | R$ 1.350.000,00 |\n"
            "| Total Anual | R$ 20.590.000,00 | 36,3% | R$ 5.720.000,00 | R$ 4.035.000,00 |\n\n"
            "Nota Explicativa 1: Normas IFRS cumpridas.\n"
        )
        return mock_output, 210.0, 1150, 280

    system_prompt = (
        "Você é um especialista em OCR e estruturação de documentos em Markdown.\n"
        "SEU OBJETIVO:\n"
        "Transcrever EXCLUSIVAMENTE a página alvo para GitHub Flavored Markdown (GFM).\n\n"
        "REGRAS RÍGIDAS:\n"
        "1. Hierarquia de Cabeçalhos:\n"
        "   - Use o nível correto de cabeçalho (#, ##, ###, ####). Não invente títulos inexistentes.\n"
        "2. Tabelas:\n"
        "   - Converta todas as tabelas em Markdown GFM puro (| Col 1 | Col 2 |).\n"
        "3. Figuras e Elementos Visuais:\n"
        "   - Para cada figura ou gráfico, use a anotação:\n"
        "     > **[Figura X: Título/Legenda]**\n"
        "     > *Descrição visual*: [Descreva detalhadamente o gráfico e tendências].\n"
        "4. Retorne APENAS o código Markdown sem blocos ```markdown envolventes.\n"
        "5. Idioma do Documento: Redija todas as descrições rigorosamente no idioma predominante da página."
    )

    effective_prompt = prompt_instructions or "Transcreva com alta fidelidade a página em anexo:"

    user_content: list[dict[str, Any]] = [
        {"type": "text", "text": effective_prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
        },
    ]

    start_t = time.perf_counter()
    response = await client.chat.completions.create(
        model=model_name,
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
    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    content = str(response.choices[0].message.content or "").strip()
    usage = response.usage
    p_tok = usage.prompt_tokens if usage else 1200
    c_tok = usage.completion_tokens if usage else 300

    return content, elapsed_ms, p_tok, c_tok


async def evaluate_models(
    models: list[str],
    scenarios: list[GroundTruthScenario],
    api_key: str | None,
    dry_run: bool = False,
    save_artifacts: bool = False,
    artifacts_dir: str = "./data/eval_ocr",
) -> list[OcrEvalResult]:
    client = None
    if not dry_run and api_key:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://agentic-substrate.local",
                "X-Title": "Agentic Substrate OCR Eval",
            },
        )

    results: list[OcrEvalResult] = []
    mode_str = "DRY-RUN (Simulado)" if dry_run or not api_key else "OPENROUTER LIVE"

    print("\n" + "=" * 90)
    print("🔬 INICIANDO BENCHMARK DE MODELOS DE VISÃO OCR (8B vs 32B)")
    print(f"Modelos: {', '.join(models)}")
    print(f"Cenários: {', '.join(s.name for s in scenarios)}")
    print(f"Modo de Execução: {mode_str}")
    print("=" * 90 + "\n")

    if save_artifacts:
        Path(artifacts_dir).mkdir(parents=True, exist_ok=True)

    for model in models:
        mod_short = model.split("/")[-1]
        print(f"🤖 Avaliando modelo: [{model}]")

        for scenario in scenarios:
            print(f"   ⏳ Processando cenário [{scenario.name}]...", end=" ", flush=True)

            if save_artifacts:
                scen_img_path = Path(artifacts_dir) / f"{scenario.name}.jpg"
                if not scen_img_path.exists():
                    scen_img_path.write_bytes(scenario.image_bytes)

            try:
                content, lat_ms, p_tok, c_tok = await execute_ocr_call(
                    client=client,
                    model_name=model,
                    image_bytes=scenario.image_bytes,
                    dry_run=dry_run,
                )

                eval_res = compute_metrics(
                    output_md=content,
                    scenario=scenario,
                    latency_ms=lat_ms,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    model_name=model,
                )
                results.append(eval_res)

                if save_artifacts:
                    out_md_path = (
                        Path(artifacts_dir) / f"{mod_short}_{scenario.name}.md"
                    )
                    out_md_path.write_text(content, encoding="utf-8")

                print(
                    f"✅ OK ({eval_res.latency_ms:.0f}ms | "
                    f"Tokens: {eval_res.total_tokens} | "
                    f"Qualidade: {eval_res.overall_quality_pct:.1f}% | "
                    f"Custo/1k págs: ${eval_res.cost_per_1k_pages_usd:.2f})"
                )

            except Exception as e:
                print(f"❌ ERRO: {e}")
                err_res = OcrEvalResult(
                    model_name=model,
                    scenario_name=scenario.name,
                    latency_ms=0.0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    estimated_cost_usd=0.0,
                    cost_per_1k_pages_usd=0.0,
                    table_score_pct=0.0,
                    heading_score_pct=0.0,
                    keyword_recall_pct=0.0,
                    figure_score_pct=0.0,
                    overall_quality_pct=0.0,
                    success=False,
                    markdown_output="",
                    error_message=str(e),
                )
                results.append(err_res)

        print()

    return results


def print_consolidated_report(results: list[OcrEvalResult]) -> None:
    print("\n" + "=" * 105)
    print("📊 RESULTADOS CONSOLIDADOS DO BENCHMARK OCR MULTIMODAL")
    print("=" * 105)
    header = (
        f"{'Modelo':<28} | {'Cenário':<22} | {'Latência':<9} | "
        f"{'Tabela %':<8} | {'Header %':<8} | {'Recall %':<8} | {'Score %':<7} | {'$/1k págs':<9}"
    )
    print(header)
    print("-" * 105)

    for r in results:
        mod_short = r.model_name.split("/")[-1] if "/" in r.model_name else r.model_name
        lat_str = f"{r.latency_ms:.0f}ms" if r.success else "FALHA"
        cost_str = f"${r.cost_per_1k_pages_usd:.2f}" if r.success else "N/A"
        print(
            f"{mod_short:<28} | {r.scenario_name:<22} | {lat_str:>9} | "
            f"{r.table_score_pct:>8.1f} | {r.heading_score_pct:>8.1f} | "
            f"{r.keyword_recall_pct:>8.1f} | {r.overall_quality_pct:>7.1f} | {cost_str:>9}"
        )
    print("=" * 105 + "\n")

    # Análise Comparativa Agregada
    models = list(dict.fromkeys(r.model_name for r in results if r.success))
    if len(models) >= 2:
        print("📈 ANÁLISE COMPARATIVA DE EFICIÊNCIA (ROI, SPEEDUP & ECONOMIA):")
        print("-" * 80)
        m_stats: dict[str, dict[str, float]] = {}
        for m in models:
            m_res = [r for r in results if r.model_name == m and r.success]
            if not m_res:
                continue
            avg_lat = sum(r.latency_ms for r in m_res) / len(m_res)
            avg_score = sum(r.overall_quality_pct for r in m_res) / len(m_res)
            avg_cost_1k = sum(r.cost_per_1k_pages_usd for r in m_res) / len(m_res)
            m_stats[m] = {
                "lat": avg_lat,
                "score": avg_score,
                "cost_1k": avg_cost_1k,
            }

        ref_model = models[-1]  # Ex: 32b
        cand_model = models[0]  # Ex: 8b

        if ref_model in m_stats and cand_model in m_stats:
            ref_lat = m_stats[ref_model]["lat"]
            cand_lat = m_stats[cand_model]["lat"]
            ref_cost = m_stats[ref_model]["cost_1k"]
            cand_cost = m_stats[cand_model]["cost_1k"]
            ref_score = m_stats[ref_model]["score"]
            cand_score = m_stats[cand_model]["score"]

            speedup = (ref_lat / cand_lat) if cand_lat > 0 else 1.0
            savings = ((ref_cost - cand_cost) / ref_cost * 100.0) if ref_cost > 0 else 0.0
            delta_qual = cand_score - ref_score

            print(f"• Modelo Base (Referência):   {ref_model}")
            print(f"  - Latência Média:           {ref_lat:.0f}ms por página")
            print(f"  - Custo Estimado:           ${ref_cost:.2f} / 1.000 páginas")
            print(f"  - Qualidade Média:          {ref_score:.1f}%\n")

            print(f"• Modelo Candidato (Lean):     {cand_model}")
            print(f"  - Latência Média:           {cand_lat:.0f}ms por página")
            print(f"  - Custo Estimado:           ${cand_cost:.2f} / 1.000 páginas")
            print(f"  - Qualidade Média:          {cand_score:.1f}%\n")

            print("🏆 VEREDITO DO BENCHMARK:")
            print(f"  ⚡ Velocidade:   {speedup:.1f}x mais rápido")
            print(f"  💰 Economia:     {savings:.1f}% de redução de custo")
            print(f"  🎯 Qualidade:    {delta_qual:+.1f}% de diferença de fidelidade")
        print("=" * 80 + "\n")


async def load_scenarios_from_pdf(
    pdf_path: str, max_pages: int = 3
) -> list[GroundTruthScenario]:
    """Carrega páginas de um PDF real usando o PdfPageRenderer do sistema."""
    renderer = PdfPageRenderer(high_res_scale=2.0)
    pdf_bytes = Path(pdf_path).read_bytes()
    page_count = await renderer.get_page_count(pdf_bytes)
    pages_to_eval = min(max_pages, page_count)

    scenarios: list[GroundTruthScenario] = []
    for i in range(pages_to_eval):
        b64_img = await renderer.render_page_high_res(pdf_bytes, i)
        img_bytes = base64.b64decode(b64_img)
        scenarios.append(
            GroundTruthScenario(
                name=f"PDF_Pagina_{i+1}",
                description=f"Página {i+1} de {page_count} do arquivo {Path(pdf_path).name}",
                image_bytes=img_bytes,
                expected_keywords=[],
            )
        )
    return scenarios


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Eval & Benchmark Suite para Modelos de Visão Multimodal de OCR."
    )
    parser.add_argument(
        "--models",
        type=str,
        default="qwen/qwen3-vl-8b-instruct,qwen/qwen3-vl-32b-instruct",
        help="Modelos separados por vírgula para avaliar (ex: qwen/qwen3-vl-8b-instruct,qwen/qwen3-vl-32b-instruct)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("OPENROUTER_API_KEY"),
        help="Chave de API OpenRouter",
    )
    parser.add_argument(
        "--pdf-path",
        type=str,
        default=None,
        help="Caminho para arquivo PDF real para avaliar páginas reais em vez de cenários sintéticos",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=3,
        help="Número máximo de páginas para avaliar quando --pdf-path for fornecido (default: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa em modo simulado sem chamadas reais de API",
    )
    parser.add_argument(
        "--save-artifacts",
        action="store_true",
        help="Salva imagens de teste e outputs em Markdown em ./data/eval_ocr para auditoria",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default="./data/eval_ocr",
        help="Diretório onde salvar artefatos gerados (default: ./data/eval_ocr)",
    )

    args = parser.parse_args()
    model_list = [m.strip() for m in args.models.split(",") if m.strip()]

    if args.pdf_path:
        if not Path(args.pdf_path).exists():
            print(f"ERRO: Arquivo PDF '{args.pdf_path}' não encontrado.", file=sys.stderr)
            sys.exit(1)
        scenarios = asyncio.run(load_scenarios_from_pdf(args.pdf_path, args.max_pages))
    else:
        scenarios = [
            generate_synthetic_table_scenario(),
            generate_synthetic_hierarchy_scenario(),
            generate_synthetic_chart_scenario(),
        ]

    results = asyncio.run(
        evaluate_models(
            models=model_list,
            scenarios=scenarios,
            api_key=args.api_key,
            dry_run=args.dry_run,
            save_artifacts=args.save_artifacts,
            artifacts_dir=args.artifacts_dir,
        )
    )
    print_consolidated_report(results)


if __name__ == "__main__":
    main()
