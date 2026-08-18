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
        "X-Title": "Agentic Substrate Hierarchical ToC Test",
    },
)

def render_low_res_page(page: pdfium.PdfPage) -> str:
    pil_image = page.render(scale=1.0).to_pil()
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    buffer = BytesIO()
    pil_image.save(buffer, format="JPEG", quality=70)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

async def test_hierarchical_json_inference(pdf_path: str):
    doc = pdfium.PdfDocument(pdf_path)
    total_pages = len(doc)
    print("=== TESTE DE INFERÊNCIA HIERÁRQUICA ESTRITA (SEÇÃO vs SUBSEÇÃO) ===")
    print(f"Documento: {pdf_path} ({total_pages} páginas)")
    
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

    system_prompt = """Você é um especialista em análise ontológica e estrutural de documentos.

SEU OBJETIVO:
Analisar as páginas visuais do documento e produzir a Árvore Hierárquica Completa inferindo com precisão matemática a relação de Seções e Subseções.

SCHEMA JSON DE SAÍDA:
Retorne uma lista de objetos com a seguinte estrutura para cada cabeçalho identificado:
[
  {
    "type": "document_title" | "section" | "subsection" | "sub_subsection",
    "markdown_level": "#" | "##" | "###" | "####",
    "title": "Texto exato do título com numeração original",
    "page": número_da_página_onde_começa,
    "parent_section": "Título da Seção Pai correspondente (ou null se for seção principal ou título do doc)"
  }
]

REGRAS:
1. "document_title" (#): Título principal do artigo/documento na primeira página. parent_section: null.
2. "section" (##): Grandes seções principais (ex: 1. Introduction, 2. Methods, 3. Results/Discussion, 4. Conclusions). parent_section: null.
3. "subsection" (###): Subseções subordinadas a uma grande seção (ex: 2.1 Literature Search pertence a 2. Methods). parent_section deve conter exatamente "2. Methods".
4. "sub_subsection" (####): Tópicos subordinados a uma subseção.
5. Retorne EXCLUSIVAMENTE o JSON válido, sem comentários ou blocos markdown de explicação.
"""
    content_payload.append({
        "type": "text",
        "text": "Gere agora a árvore hierárquica em JSON identificando claramente seções, subseções e suas seções pai (parent_section)."
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
    
    print("\n--- JSON HIERÁRQUICO INFERIDO PELO QWEN3-VL ---")
    print(raw_content)

if __name__ == "__main__":
    pdf = "/Users/insider/Downloads/ijerph-16-04897-v2.pdf"
    asyncio.run(test_hierarchical_json_inference(pdf))
