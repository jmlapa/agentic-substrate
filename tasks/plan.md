# Implementation Plan: Ingestion Saga Concurrency Resilience & Deferred Atomic Commit (Marco 1.26)

## 1. Overview
Implementar o padrão **Deferred Atomic Commit with Optimistic Retry** no `DocumentIngestionSagaCoordinator`, eliminando colisões de concorrência (`DomainError: Concurrency conflict`) no PostgreSQL Event Store quando múltiplos documentos pertencentes à mesma Knowledge Base são processados em paralelo. Garantir que 100% dos documentos completem o pipeline até o estado `INDEXED` (ou `FAILED` com mensagem de erro registrada), e recuperar os documentos atualmente travados no estado `CHUNKED`.

---

## 2. Architecture Decisions
- **Desacoplamento do I/O Lento do Lock de Domínio:** Todas as etapas pesadas (LLM, embeddings, OCR, FalkorDB) executam em paralelo assíncrono sem reter instâncias de agregados nem travar locks.
- **Janela de Commit Atômico Reduzida a ~5ms:** Apenas no término da computação, a saga recarrega o agregado do PostgreSQL, aplica a mutação de domínio e persiste o evento.
- **Mutex Local por Knowledge Base (`asyncio.Lock`):** Serializa a fase de reload-mutate-commit no processo para a mesma KB.
- **Retry Loop com Backoff Jittered:** Caso ocorra conflito de concorrência (ex: réplicas concorrentes ou race condition), realiza até 5 tentativas imediatas recarregando a versão mais recente do aggregate.
- **Tratamento Seguro de Exceções:** O bloco `except Exception` também utiliza a mutação atômica para gravar `mark_processing_failed`, garantindo que documentos nunca fiquem em estado órfão/inconsistente.
- **Single Class per File & Mypy Strict:** Conformidade irrestrita com as regras do repositório (`AGENTS.md`).

---

## 3. Dependency Graph

```
[Phase 1] Saga Coordinator: Deferred Atomic Commit, Mutex por KB e Retry Loop
    │
    ├── [Phase 2] ReprocessDocumentUseCase: Suporte à Retomada de Documentos Intermediários
    │       │
    │       └── [Phase 3] Testes Automatizados de Concorrência e Resiliência
    │               │
    │               └── [Phase 4] Verificação de Gates (make pre-commit) e Recuperação dos Documentos em Produção
```

---

## 4. Phase Breakdown

### Phase 1: Saga Coordinator Refactoring (Tasks 1 & 2)
- Adicionar mapa de locks por KB (`_kb_locks`) e helper `_execute_atomic_aggregate_mutation` com retry exponencial e jitter no `DocumentIngestionSagaCoordinator`.
- Refatorar todos os handlers da saga (`handle_document_stored`, `handle_document_parsed`, `handle_document_chunked`, `handle_graph_extracted`) para usar o helper de commit atômico tanto no sucesso quanto na captura de exceções.

### Phase 2: Reprocess Document Use Case Enhancement (Task 3)
- Atualizar `ReprocessDocumentUseCase` para permitir reprocessamento a partir de qualquer estado não-terminal (`CHUNKED`, `PARSED`, `FAILED`), republicando o evento correspondente para que a saga retome usando o cache em disco.

### Phase 3: Automated Testing Suite (Task 4)
- Criar `tests/modules/knowledge/application/test_document_ingestion_saga_concurrency.py` com cenários de concorrência simulada (5 documentos simultâneos na mesma KB) e injeção de conflito de concorrência para validar o retry loop.

### Phase 4: Quality Gates & Live Recovery (Tasks 5 & 6)
- Executar `make pre-commit` para validar Ruff, Mypy Strict e Pytest com 100% de sucesso.
- Reiniciar `substrate_api` e disparar o reprocessamento dos documentos pendentes (`4483722f...`, `5506c4df...`, `b93ce975...`), validando que todos atingem o status `INDEXED`.
