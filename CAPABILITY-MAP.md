# Capability Map: Agentic Substrate

| Module id | Responsibility | Depends on | Status |
|---|---|---|---|
| `kernel` | Primitivas compartilhadas puras (Entity, ValueObject, AggregateRoot, DomainEvent, Result/Either), contratos de Event Sourcing, interfaces de EventBus e abstrações base. | — | In Progress |
| `knowledge` | Pipeline assíncrono GraphRAG: ingestão particionada por KB em Object Storage, Saga coreografada com Event Sourcing, parser para Markdown, extração ontológica estruturada dinâmica com Pydantic em runtime, indexação vetorial e em grafo. | `kernel` | In Progress |
| `api-gateway` | Exposição HTTP/REST assíncrona (FastAPI), injeção de dependências, orquestração de endpoints para gerenciamento de KBs, upload particionado e consultas semânticas/grafo. | `kernel`, `knowledge` | In Progress |
| `memory` | Memória de curto/longo prazo para agentes, histórico de diálogos, grafos de memória episódica/semântica. | `kernel` | Backlog |
| `tool-registry` | Registro, validação e governança de tools executáveis por agentes. | `kernel` | Backlog |
| `execution` | Máquina de estados de execução de agentes e orquestração de sessões. | `kernel`, `memory`, `knowledge`, `tool-registry` | Backlog |

## Ordem de Construção (Marco 1)
`kernel` ──→ `knowledge` ──→ `api-gateway`
