# Capability Map: Agentic Substrate

| Module id | Responsibility | Depends on | Status |
|---|---|---|---|
| `kernel` | Primitivas compartilhadas puras (Entity, ValueObject, AggregateRoot, DomainEvent, Result/Either), contratos de Event Sourcing, interfaces de EventBus, PostgresEventStore com concorrência otimista, controle de vazão (AsyncTokenBucketLimiter) e abstrações base. | — | Completed (v0.2.0) |
| `knowledge` | Pipeline assíncrono GraphRAG: ingestão particionada por KB em Local FileSystem Storage, Saga coreografada com Event Sourcing, parser MarkItDown (com suporte a PDFs de alta resolução), chunking hierárquico tolerante à estrutura (StructureTolerantMarkdownChunker), embeddings Gemini 2 com MRL (768d), extração ontológica com PydanticAI v2, rate limiting (300 RPM / 1M TPM), canonização cumulativa de entidades e indexação híbrida no FalkorDB. | `kernel` | Completed (v0.2.0) |
| `api-gateway` | Exposição HTTP/REST assíncrona (FastAPI), container de injeção de dependências (IoC), orquestração de endpoints para gerenciamento de KBs, templates de ontologia, upload particionado e consultas híbridas GraphRAG com subgrafos e nós ontológicos. | `kernel`, `knowledge` | Completed (v0.2.0) |
| `frontend-console` | Console SPA leve (Vite, React, TypeScript, Tailwind CSS) para gestão de ontologias, criação e listagem de KBs, upload de documentos, monitoramento visual em tempo real por etapas de pipeline e playground de consulta RAG com LLM. | `api-gateway` | Completed (v0.2.1) |
| `memory` | Memória de curto/longo prazo para agentes, histórico de diálogos, grafos de memória episódica/semântica. | `kernel` | Backlog (v0.3.0) |
| `tool-registry` | Registro, validação e governança de tools executáveis por agentes. | `kernel` | Backlog (v0.4.0) |
| `execution` | Máquina de estados de execução de agentes e orquestração de sessões. | `kernel`, `memory`, `knowledge`, `tool-registry` | Backlog (v0.5.0) |

## Especificações Técnicas
- `SPEC-knowledge-substrate.md` (Marco 1 & 1.5 - Substrato Base de Knowledge) — Concluído
- `SPEC-knowledge-chunking-and-embeddings.md` (Marco 1.6 - Markdown Parent-Child Chunking & Gemini Embedding 2) — Concluído
- `SPEC-unified-falkordb-hybrid-graphrag.md` (Marco 1.7 - FalkorDB Hybrid GraphRAG Unificado) — Concluído
- `SPEC-markdown-structure-tolerant-chunker.md` (Marco 1.8 - Universal Structure-Tolerant Markdown Chunker) — Concluído
- `SPEC-pydantic-ai-graph-extractor-and-rate-limiter.md` (Marco 1.9 - PydanticAI Graph Extractor, Rate Limiter RPM/TPM & Entity Canonicalization) — Concluído
- `SPEC-frontend-console.md` (Marco 1.10 - Frontend Console SPA & RAG Query Playground) — Concluído

## Architecture Decision Records (ADRs)
- `docs/decisions/0001-hexagonal-event-sourced-architecture.md`
- `docs/decisions/0002-unified-falkordb-hybrid-graphrag.md`
- `docs/decisions/0003-pydantic-ai-graph-extractor-and-rate-limiter.md`
- `docs/decisions/0004-universal-structure-tolerant-chunker.md`

## Ordem de Construção
1. **Marco 1 & 1.5 (Concluído):** `kernel` ──→ `knowledge` ──→ `api-gateway` (com infraestrutura real local: Postgres, FalkorDB, Redis, Local Storage)
2. **Marco 1.6 & 1.7 (Concluído):** `knowledge:chunking-and-embeddings` & `knowledge:falkordb-hybrid-graphrag`
3. **Marco 1.8 & 1.9 (Concluído):** `knowledge:structure-tolerant-chunker` ──→ `knowledge:pydantic-ai-extractor-and-rate-limiter`
4. **Marco 1.10 (Atual):** `frontend-console` (Vite+React SPA, Ontologias, KBs, Monitor de Pipeline, Playground RAG) ──→ `api-gateway` (fechamento do ciclo de query com LLM)
5. **Marco 2 (Próximo):** `memory` ──→ `tool-registry` ──→ `execution`
