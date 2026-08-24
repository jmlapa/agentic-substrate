# Capability Map: Agentic Substrate

| Module id | Responsibility | Depends on | Status |
|---|---|---|---|
| `kernel` | Primitivas compartilhadas puras (Entity, ValueObject, AggregateRoot, DomainEvent, Result/Either), contratos de Event Sourcing, interfaces de EventBus, PostgresEventStore com concorrência otimista, controle de vazão (AsyncTokenBucketLimiter) e abstrações base. | — | Completed (v0.2.0) |
| `knowledge` | Pipeline assíncrono GraphRAG: ingestão particionada por KB em Local FileSystem Storage, Saga coreografada com Event Sourcing, parser MarkItDown (com fast-path nativo zero-cost e OCR multimodal via OpenRouter/Qwen3-VL), chunking hierárquico tolerante à estrutura (StructureTolerantMarkdownChunker), embeddings Gemini 2 com MRL (768d), extração ontológica com PydanticAI v2 (OpenRouter/Google Gemma 4 e Gemini), rate limiting (300 RPM / 1M TPM), canonização cumulativa de entidades e indexação híbrida no FalkorDB. | `kernel` | Completed (v0.3.0) |
| `api-gateway` | Exposição HTTP/REST assíncrona (FastAPI), container de injeção de dependências (IoC), orquestração de endpoints para gerenciamento de KBs, templates de ontologia, upload particionado com opções de OCR e consultas híbridas GraphRAG com subgrafos e nós ontológicos. | `kernel`, `knowledge` | Completed (v0.3.0) |
| `frontend-console` | Console SPA leve (Vite, React, TypeScript, Tailwind CSS) para gestão de ontologias, criação e listagem de KBs, upload de documentos com toggle de OCR e instruções customizadas de Markdown, monitoramento visual em tempo real por etapas de pipeline e playground de consulta RAG com LLM. | `api-gateway` | Completed (v0.3.0) |
| `memory` | Memória de curto/longo prazo para agentes, histórico de diálogos, grafos de memória episódica/semântica. | `kernel` | Backlog (v0.4.0) |
| `tool-registry` | Registro, validação e governança de tools executáveis por agentes. | `kernel` | Backlog (v0.5.0) |
| `execution` | Máquina de estados de execução de agentes e orquestração de sessões. | `kernel`, `memory`, `knowledge`, `tool-registry` | Backlog (v0.6.0) |

## Especificações Técnicas
- `SPEC-knowledge-substrate.md` (Marco 1 & 1.5 - Substrato Base de Knowledge) — Concluído
- `SPEC-knowledge-chunking-and-embeddings.md` (Marco 1.6 - Markdown Parent-Child Chunking & Gemini Embedding 2) — Concluído
- `SPEC-unified-falkordb-hybrid-graphrag.md` (Marco 1.7 - FalkorDB Hybrid GraphRAG Unificado) — Concluído
- `SPEC-markdown-structure-tolerant-chunker.md` (Marco 1.8 - Universal Structure-Tolerant Markdown Chunker) — Concluído
- `SPEC-pydantic-ai-graph-extractor-and-rate-limiter.md` (Marco 1.9 - PydanticAI Graph Extractor, Rate Limiter RPM/TPM & Entity Canonicalization) — Concluído
- `SPEC-frontend-console.md` (Marco 1.10 - Frontend Console SPA & RAG Query Playground) — Concluído
- `SPEC-configurable-ocr-and-visual-ingestion.md` (Marco 1.11 - OCR Multimodal Configurável, OpenRouter & MarkItDown Custom Structure) — Concluído (v0.3.0)
- `SPEC-consolidated-read-model-projections.md` (Marco 1.12 - CQRS Consolidated Read Model & Event-Driven Projections) — Concluído (v0.3.1)
- `SPEC-gemma-4-fact-dense-rag-synthesis.md` (Marco 1.13 - OpenRouter Gemma 4 Fact-Dense RAG Synthesis & Dual-Mode Retrieval) — Concluído (v0.3.2)
- `SPEC-synthetic-toc-and-parallel-vlm-ocr.md` (Marco 1.14 - Stateful Synthetic ToC & Resilient Parallel VLM OCR) — Concluído (v0.3.3)
- `SPEC-optimized-graphrag-retrieval-and-budgeting.md` (Marco 1.15 - Optimized GraphRAG Retrieval, Candidate Fusion & 32k Token Budgeting) — Concluído (v0.3.4)
- `SPEC-resilient-saga-reprocessing-and-job-queues.md` (Marco 1.16 - Resilient Saga Reprocessing, Redis Job Queues & Zero-Token-Waste Checkpoints) — Planejado (v0.3.5)
- `SPEC-multimodal-ingestion-and-source-filtering.md` (Marco 1.17 - Multimodal Ingestion Audio/Image, Source & Temporal Filtering) — Em Andamento (v0.3.6)
- `SPEC-notes-portal-explorer.md` (Marco 1.18 - Smart Notes Portal & Document Explorer) — Especificado (v0.3.7)
- `SPEC-markdown-continuity-normalizer.md` (Marco 1.19 - Markdown Continuity Normalizer) — Concluído (v0.3.8)

## Architecture Decision Records (ADRs)
- `docs/decisions/0001-hexagonal-event-sourced-architecture.md`
- `docs/decisions/0002-unified-falkordb-hybrid-graphrag.md`
- `docs/decisions/0003-pydantic-ai-graph-extractor-and-rate-limiter.md`
- `docs/decisions/0004-universal-structure-tolerant-chunker.md`
- `docs/decisions/0005-configurable-ocr-and-openrouter-vlm.md`
- `docs/decisions/0006-cqrs-read-model-projections.md`
- `docs/decisions/0007-openrouter-gemma-4-fact-dense-rag-synthesis.md`
- `docs/decisions/0008-optimized-graphrag-retrieval-and-budgeting.md`
- `docs/decisions/0009-bounded-multiplicative-graph-decay-and-natural-deduplication.md`

## Ordem de Construção
1. **Marco 1 & 1.5 (Concluído):** `kernel` ──→ `knowledge` ──→ `api-gateway` (com infraestrutura real local: Postgres, FalkorDB, Redis, Local Storage)
2. **Marco 1.6 & 1.7 (Concluído):** `knowledge:chunking-and-embeddings` & `knowledge:falkordb-hybrid-graphrag`
3. **Marco 1.8 & 1.9 (Concluído):** `knowledge:structure-tolerant-chunker` ──→ `knowledge:pydantic-ai-extractor-and-rate-limiter`
4. **Marco 1.10 (Concluído):** `frontend-console` (Vite+React SPA, Ontologias, KBs, Monitor de Pipeline, Playground RAG)
5. **Marco 1.11 (Concluído - v0.3.0):** `knowledge:configurable-ocr-and-visual-ingestion` (OpenRouter, Fast-Path MarkItDown, Qwen3-VL, Gemma 4)
6. **Marco 1.12 (Concluído - v0.3.1):** `knowledge:cqrs-consolidated-read-model-projections` (Event-Driven Projector, Migration 0006, O(1) Relational Queries)
7. **Marco 1.13 (Concluído - v0.3.2):** `knowledge:openrouter-gemma-4-fact-dense-rag-synthesis` (Google Gemma 4 via OpenRouter, Fact-Dense Markdown, Dual-Mode synthesis/retrieve)
8. **Marco 1.14 (Concluído - v0.3.3):** `knowledge:synthetic-toc-and-parallel-vlm-ocr` (Stateful Rolling Window ToC, Parallel Two-Pass OCR, Concurrency & Rate Limiting)
9. **Marco 1.15 (Concluído - v0.3.9):** `knowledge:optimized-graphrag-retrieval-and-budgeting` (FalkorDB Cypher, Deduplicação Natural de Sementes, Bounded Multiplicative Decay, 32k Dynamic Budgeting, XML Context Injection Defense)
10. **Marco 1.19 (Concluído - v0.3.8):** `knowledge:markdown-continuity-normalizer` (Continuous Markdown Normalizer, Header Deduplication, Inter-Page Continuity Rules)
11. **Marco 2 (Próximo):** `memory` ──→ `tool-registry` ──→ `execution`


