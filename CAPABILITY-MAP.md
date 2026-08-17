# Capability Map: Agentic Substrate

| Module id | Responsibility | Depends on | Status |
|---|---|---|---|
| `kernel` | Primitivas compartilhadas puras (Entity, ValueObject, AggregateRoot, DomainEvent, Result/Either), contratos de Event Sourcing, interfaces de EventBus, PostgresEventStore com concorrência otimista e abstrações base. | — | Completed (v0.1.0) |
| `knowledge` | Pipeline assíncrono GraphRAG: ingestão particionada por KB em Local FileSystem Storage, Saga coreografada com Event Sourcing, parser MarkItDown, chunking hierárquico Markdown Parent-Child, embeddings Gemini 2 com MRL e resiliência a 429, extração ontológica estruturada dinâmica com Pydantic em runtime, indexação vetorial (pgvector) e em grafo (FalkorDB). | `kernel` | In Progress (v0.2.0) |
| `api-gateway` | Exposição HTTP/REST assíncrona (FastAPI), container de injeção de dependências (IoC), orquestração de endpoints para gerenciamento de KBs, templates de ontologia, upload particionado e consultas semânticas/grafo. | `kernel`, `knowledge` | Completed (v0.1.0) |
| `memory` | Memória de curto/longo prazo para agentes, histórico de diálogos, grafos de memória episódica/semântica. | `kernel` | Backlog |
| `tool-registry` | Registro, validação e governança de tools executáveis por agentes. | `kernel` | Backlog |
| `execution` | Máquina de estados de execução de agentes e orquestração de sessões. | `kernel`, `memory`, `knowledge`, `tool-registry` | Backlog |

## Especificações Técnicas Ativas
- `SPEC-knowledge-substrate.md` (Marco 1 & 1.5 - Substrato Base de Knowledge)
- `SPEC-knowledge-chunking-and-embeddings.md` (Marco 1.6 - Markdown Parent-Child Chunking & Gemini Embedding 2)

## Ordem de Construção
1. **Marco 1 & 1.5 (Concluído):** `kernel` ──→ `knowledge` ──→ `api-gateway` (com infraestrutura real local: Postgres/pgvector, FalkorDB, Redis, Local Storage)
2. **Marco 1.6 (Em Execução):** `knowledge:chunking-and-embeddings` (Recursive Markdown Chunker + Gemini Embedding 2 + PgVector Document Chunks + Saga Ingestion)
3. **Marco 2 (Próximo):** `memory` ──→ `tool-registry` ──→ `execution`
