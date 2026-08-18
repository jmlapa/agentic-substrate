# Sliding-Window Multimodal OCR & Strict Hierarchical Markdown Parser

## Problem Statement
Como poderíamos converter PDFs complexos (artigos científicos de múltiplas colunas, relatórios financeiros e técnicos) em Markdown estritamente hierárquico (#, ##, ###), com tabelas GFM íntegras e descrições semânticas de figuras/diagramas, eliminando a quebra de contexto entre páginas através de uma janela deslizante (Sliding Window) com VLMs (ex: Qwen3-VL / Gemini Flash)?

---

## Recommended Direction
Substituir a dependência direta do parser de PDF do `MarkItDown` por um pipeline customizado de visão computacional assíncrona:
1. **Renderização Determinística de Páginas:** Renderizar páginas do PDF em memória (via `pypdfium2`) em escala 2.0x (JPEG comprimido).
2. **Janela Deslizante de Contexto Multi-Página:** 
   - Para cada página alvo $N$, enviar imagens das páginas $N-2$ e $N-1$ como contexto puramente informativo (somente leitura).
   - Injetar no prompt o último nível de cabeçalho ativo (`active_heading_hint`) para evitar quebra de hierarquia em páginas sem título no topo.
3. **Gramática Rígida de Markdown:**
   - `#` reservado exclusivamente para o título principal do documento.
   - `##`, `###`, `####` alinhados com a numeração e seções lógicas.
   - Tags estruturadas padronizadas para figuras: `> **[Figura X: ...]** > *Descrição visual*: ...`.
   - Tabelas estritamente em GitHub Flavored Markdown (GFM).
4. **Fallback Inteligente:**
   - Manter o fast-path nativo zero-cost quando `enable_ocr=False`.
   - Ativar o sliding-window VLM quando `enable_ocr=True`.

---

## Key Assumptions & Validação na POC
- [x] **Continuidade de Frases entre Páginas:** Validada com sucesso no PDF `ijerph-16-04897-v2.pdf` (a frase iniciada na pág 1 foi completada perfeitamente na pág 2).
- [x] **Preservação de Hierarquia (# / ## / ###):** Validada com `## 1. Introduction` (pág 1), `## 2. Methods`, `### 2.1`, `### 2.2` (pág 2).
- [x] **Interpretação e Descrição de Diagramas:** A Figura 1 (diagrama de fluxo PRISMA) foi decomposta em texto com todos os números e caixas transcritos.
- [ ] **Throughput e Concorrência:** Com 3 imagens por requisição, o tempo varia entre 4s e 30s por página. Para PDFs de 50+ páginas, deve-se implementar paralelismo particionado em lotes com rate limiter de tokens.

---

## MVP Scope

### In Scope
1. **Adaptador `StructuredPdfVlmParser` ou extensão do `MarkItDownDocumentParser`**:
   - Detecção de arquivos PDF quando `enable_ocr=True`.
   - Renderização com `pypdfium2`.
   - Execução assíncrona com sliding window de até 2 páginas anteriores.
2. **Suporte a OpenRouter / Qwen3-VL / Gemini Flash**:
   - Utilizar o cliente configurado via `OpenRouterClientFactory`.
3. **Controle de Estado de Cabeçalhos**:
   - Feedback em tempo real do cabeçalho anterior no prompt da página atual.

### Not Doing (and Why)
- **OCR local com Tesseract/PaddleOCR:** Não gera hierarquia Markdown semântica nem descreve diagramas com inteligência contextual.
- **Processamento de PDF puro via pdfminer no modo OCR:** Perde o layout de múltiplas colunas e a interpretação de gráficos.

---

## Open Questions & Trade-offs
1. **Otimização de Contexto:** Passar imagens de baixa resolução para as páginas de contexto ($N-2, N-1$) e alta resolução apenas para a página alvo $N$, reduzindo o tempo de inferência e o consumo de tokens no OpenRouter.
2. **Integração no Ecossistema:** Manter o nome `MarkItDownDocumentParser` como facade para o contrato `IDocumentParser` para manter retrocompatibilidade com a Saga de Ingestão.
