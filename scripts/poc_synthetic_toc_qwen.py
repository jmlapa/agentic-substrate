import asyncio
import base64
import os
import sys
import time
from io import BytesIO

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
        "X-Title": "Agentic Substrate Synthetic ToC Test",
    },
)

def render_low_res_page(page: pdfium.PdfPage) -> str:
    # Renderiza em baixa resolução (scale 1.0x / ~72-100 DPI) para ser ultra-rápido e leve em tokens
    pil_image = page.render(scale=1.0).to_pil()
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    buffer = BytesIO()
    pil_image.save(buffer, format="JPEG", quality=70)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

async def extract_synthetic_toc(pdf_path: str):
    doc = pdfium.PdfDocument(pdf_path)
    total_pages = len(doc)
    print("=== TESTE DE SYNTHETIC ToC COM QWEN3-VL ===")
    print(f"Documento: {pdf_path} ({total_pages} páginas)")
    print(f"Renderizando {total_pages} páginas em baixa resolução (1.0x)...")
    
    t0 = time.time()
    content_payload = []
    content_payload.append({
        "type": "text",
        "text": f"O documento possui {total_pages} páginas anexadas em sequência abaixo."
    })
    
    for i in range(total_pages):
        b64 = render_low_res_page(doc[i])
        content_payload.append({
            "type": "text",
            "text": f"[PÁGINA {i+1}]"
        })
        content_payload.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })
        
    render_time = time.time() - t0
    print(f"Renderização concluída em {render_time:.2f}s.")

    system_prompt = """Você é um especialista em análise estrutural de documentos.
SEU OBJETIVO:
Identificar a Árvore Hierárquica Completa de Títulos e Seções (Synthetic Table of Contents) do documento a partir das páginas visuais fornecidas.

REGRAS:
1. Extraia APENAS os títulos de seções reais (ex: Título Principal do Artigo, 1. Introduction, 2. Methods, 2.1 Literature Search, 3. Results, etc.).
2. Identifique o nível hierárquico correto:
   - level 1 (#): Título Principal do Documento
   - level 2 (##): Seções Principais (1. Introduction, 2. Methods, etc.)
   - level 3 (###): Subseções (2.1, 2.2, 3.1, etc.)
   - level 4 (####): Tópicos menores
3. Indique a página exata (page_number) onde o título aparece.
4. Responda ESTRITAMENTE em formato JSON (uma lista de objetos) sem markdown blocks, sem comentários:
[
  {"level": 1, "title": "...", "page": 1},
  {"level": 2, "title": "1. ...", "page": 1},
  {"level": 3, "title": "2.1 ...", "page": 2}
]
"""
    content_payload.append({
        "type": "text",
        "text": "Gere agora o JSON com o Synthetic ToC de todo o documento."
    })

    print("Enviando requisição multimodal para o Qwen3-VL...")
    t1 = time.time()
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_payload}
        ],
        temperature=0.0,
    )
    api_time = time.time() - t1
    raw_content = response.choices[0].message.content or ""
    usage = response.usage

    print(f"Resposta recebida em {api_time:.2f}s!")
    if usage:
        print(f"Tokens: {usage.prompt_tokens} prompt / {usage.completion_tokens} completion")
    
    print("\n--- SYNTHETIC ToC GERADO PELO QWEN3-VL ---")
    print(raw_content)

if __name__ == "__main__":
    pdf = "/Users/insider/Downloads/ijerph-16-04897-v2.pdf"
    asyncio.run(extract_synthetic_toc(pdf))
