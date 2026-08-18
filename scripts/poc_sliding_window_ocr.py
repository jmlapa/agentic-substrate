import argparse
import asyncio
import base64
import os
import sys
import time
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("OCR_VISION_MODEL_NAME", "qwen/qwen3-vl-30b-a3b-instruct")

if not OPENROUTER_API_KEY:
    print("ERRO: OPENROUTER_API_KEY não encontrada no .env", file=sys.stderr)
    sys.exit(1)

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://agentic-substrate.local",
        "X-Title": "Agentic Substrate POC",
    },
)

SYSTEM_PROMPT = """Você é um especialista em OCR e estruturação de documentos científicos.

SEU OBJETIVO:
Transcrever EXCLUSIVAMENTE a página identificada como [PÁGINA ATUAL / ALVO]
para GitHub Flavored Markdown (GFM), mantendo rigorosa fidelidade ao texto original
e consistência hierárquica com as páginas anteriores.

REGRAS RÍGIDAS DE ESTRUTURA E FORMATAÇÃO:
1. Hierarquia de Títulos:
   - # : Título Principal do Artigo / Documento (Apenas na página inicial onde aparece).
   - ## : Seções Principais (ex: 1. Introduction, 2. Materials and Methods, 3. Results, etc.).
   - ### : Subseções (ex: 2.1. Study Area, 2.2. Data Collection).
   - #### : Tópicos menores / Parágrafos temáticos.
   - Use o contexto das páginas anteriores para saber exatamente em qual nível hierárquico estamos.
     Se a página atual continuar uma seção sem um novo título, NÃO crie títulos artificiais.
2. Continuidade de Texto:
   - Se a primeira frase da página atual for a continuação de uma frase anterior,
     continue o texto normalmente sem quebra de parágrafo forçada.
3. Tabelas:
   - Converta TODAS as tabelas para formato GFM (| Coluna 1 | Coluna 2 |).
   - Se uma tabela começou na página anterior e continuar nesta, repita o cabeçalho das colunas.
4. Figuras e Elementos Visuais:
   - Para toda figura, mapa, gráfico ou esquema visual, use a tag:
     > **[Figura X: Título/Legenda]**
     > *Descrição visual*: [Descreva detalhadamente os elementos visuais presentes].
5. Fórmulas Matemáticas:
   - Use LaTeX inline com $...$ ou bloco $$\\n...\\n$$.
6. Saída Limpa:
   - Retorne APENAS o código Markdown da página alvo. Não envolva com ```markdown ... ```.
"""


def render_page_to_jpeg_b64(page: pdfium.PdfPage, scale: float = 2.0) -> str:
    pil_image = page.render(scale=scale).to_pil()
    # Converte para RGB se necessário
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    buffer = BytesIO()
    pil_image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


async def process_page_with_sliding_window(
    page_num: int,
    total_pages: int,
    history_images_b64: list[tuple[int, str]],
    current_image_b64: str,
    active_section_hint: str = "",
) -> str:
    messages_content: list[dict] = []

    # Adiciona páginas de contexto (N-2, N-1)
    for p_idx, b64_img in history_images_b64:
        messages_content.append(
            {
                "type": "text",
                "text": f"--- [PÁGINA {p_idx} (APENAS CONTEXTO / NÃO TRANSCREVER)] ---",
            }
        )
        messages_content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
        )

    # Adiciona a página alvo (N)
    header_text = (
        f"--- [PÁGINA {page_num} de {total_pages} (PÁGINA ATUAL / ALVO PARA TRANSCRIÇÃO)] ---\n"
        f"Contexto do último cabeçalho conhecido: '{active_section_hint}'\n"
        f"Transcreva AGORA apenas esta página {page_num} seguindo todas as regras."
    )
    messages_content.append(
        {
            "type": "text",
            "text": header_text,
        }
    )
    messages_content.append(
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{current_image_b64}"},
        }
    )

    start_time = time.time()
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": messages_content},
        ],
        temperature=0.0,
    )
    elapsed = time.time() - start_time
    content = response.choices[0].message.content or ""

    # Extrair estatísticas de uso se disponível
    usage = response.usage
    tokens_info = (
        f"{usage.prompt_tokens} prompt / {usage.completion_tokens} completion" if usage else "N/A"
    )
    print(f"  ✓ Página {page_num} processada em {elapsed:.2f}s | Tokens: {tokens_info}")

    return content.strip()


async def run_poc(pdf_path: str, max_pages: int, output_file: str):
    print("=== INICIANDO POC SLIDING WINDOW OCR ===")
    print(f"Arquivo PDF: {pdf_path}")
    print(f"Modelo: {MODEL_NAME}")
    print(f"Máximo de páginas a testar: {max_pages}")

    doc = pdfium.PdfDocument(pdf_path)
    total_doc_pages = len(doc)
    pages_to_process = min(max_pages, total_doc_pages)

    print(f"Total de páginas no documento: {total_doc_pages} | Processando: {pages_to_process}")

    # 1. Renderiza as páginas necessárias
    print(f"Renderizando {pages_to_process} páginas para JPEG...")
    rendered_pages: list[str] = []
    for i in range(pages_to_process):
        b64 = render_page_to_jpeg_b64(doc[i], scale=2.0)
        rendered_pages.append(b64)
    print("Renderização concluída.")

    # 2. Executa a janela deslizante
    full_markdown: list[str] = []
    last_heading = "Início do Documento"

    for idx in range(pages_to_process):
        page_num = idx + 1
        print(f"\n-> Processando Página {page_num}/{pages_to_process} com sliding window...")

        # Histórico: até 2 páginas anteriores
        history: list[tuple[int, str]] = []
        if idx >= 2:
            history.append((idx - 1, rendered_pages[idx - 2]))
        if idx >= 1:
            history.append((idx, rendered_pages[idx - 1]))

        page_md = await process_page_with_sliding_window(
            page_num=page_num,
            total_pages=total_doc_pages,
            history_images_b64=history,
            current_image_b64=rendered_pages[idx],
            active_section_hint=last_heading,
        )

        # Atualiza último cabeçalho identificado para feedback contínuo
        for line in page_md.splitlines():
            if line.startswith("#"):
                last_heading = line.strip()

        full_markdown.append(f"<!-- ===== PÁGINA {page_num} ===== -->\n\n{page_md}")

    # Salva resultado
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_text = "\n\n".join(full_markdown)
    output_path.write_text(final_text, encoding="utf-8")

    print("\n=== POC CONCLUÍDA COM SUCESSO! ===")
    print(f"Resultado salvo em: {output_path.resolve()}")
    print(f"Tamanho gerado: {len(final_text)} caracteres")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="POC de Sliding Window OCR com Qwen-VL")
    parser.add_argument(
        "--pdf",
        default="/Users/insider/Downloads/ijerph-16-04897-v2.pdf",
        help="Caminho do PDF",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=3,
        help="Número de páginas para processar",
    )
    parser.add_argument(
        "--output",
        default="data/poc_output_ijerph.md",
        help="Arquivo de saída Markdown",
    )
    args = parser.parse_args()

    asyncio.run(run_poc(args.pdf, args.pages, args.output))
