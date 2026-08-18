# ADR-0005: Configurable Multimodal OCR, OpenRouter VLM and PydanticAI OpenAI Provider

## Status
Accepted

## Date
2026-08-18

## Context
Document ingestion in high-volume enterprise and legal environments involves heterogeneous document types:
1. **Purely Textual Documents** (plain text, markdown, HTML, digital PDFs with intact text streams, DOCX, CSV): Routing these documents through expensive Vision-Language Models (VLMs) generates unnecessary API latency and significant token costs.
2. **Visual & Scanned Documents** (scanned PDFs, architecture diagrams, charts, tabular images): Require state-of-the-art vision models to extract complex tables, formulas, and visual diagrams into structured Markdown without losing context.
3. **Graph Extraction & RAG Synthesis**: Requires strict JSON schema adherence and reasoning capabilities at low latency and cost.

## Decision
1. **Dual-Path Document Ingestion Architecture**:
   - **Fast-Path Zero-Cost Default (`enable_ocr=False`)**: Process documents natively in CPU memory using MarkItDown without making any external LLM/VLM network calls (sub-second execution, $0.00 cost).
   - **Multimodal OCR (`enable_ocr=True`)**: Route document parsing to a Vision-Language Model via OpenRouter (`qwen/qwen3-vl-30b-a3b-instruct`) with support for custom Markdown structure instructions (*Prompt Injection*).
2. **Unified OpenRouter Gateway & Model Selection**:
   - **OCR / Vision Model**: `qwen/qwen3-vl-30b-a3b-instruct` (MoE with ~3.3B active parameters, optimal balance between optical accuracy and cost).
   - **Graph Extraction & RAG Synthesis**: `deepseek/deepseek-v4-flash` for deterministic Pydantic extraction.
3. **PydanticAI v2 Integration via Custom OpenAI Client**:
   - Create `PydanticAiOpenRouterProviderFactory` to configure `OpenAIResponsesModel` and `OpenAIProvider` with a custom `AsyncOpenAI` client.
   - Inject governance headers (`HTTP-Referer`, `X-Title`) and transport-level rate limiting (`RateLimitedAsyncTransport`).
   - Implement resilient fallback to deterministic extraction (`StructuredPydanticGraphExtractor`) in case of provider timeouts or offline testing.
4. **Frontend Control & Governance**:
   - Provide an intuitive toggle in `DocumentUploadModal.tsx` displaying real-time Fast-Path status and an expandable prompt editor for custom Markdown rules.

## Alternatives Considered

### Global Unconditional VLM OCR for All Documents
- **Pros**: Uniform pipeline.
- **Cons**: Excessive token costs ($0.05-$0.20 per document) and 10x-20x higher latency on purely textual documents.
- **Rejected**: Most enterprise documents have native digital text layers. Fast-path default saves 90%+ in LLM API expenses.

### Local Tesseract / EasyOCR in Docker
- **Pros**: No external API dependencies.
- **Cons**: Poor performance on complex tables, diagrams, and formatting; heavy Docker container images (>2GB); high CPU/GPU load on host.
- **Rejected**: Modern VLMs like Qwen3-VL produce vastly superior structured Markdown for GraphRAG.

## Consequences
- Sub-second parsing for digital text documents with zero LLM API costs.
- High-fidelity visual transcription for scanned and diagrammatic documents on demand.
- Strict Pydantic JSON validation for Knowledge Graph extraction using OpenRouter's low-latency models.
