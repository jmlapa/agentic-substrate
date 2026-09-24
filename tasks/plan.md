# Implementation Plan: Motor de Ingestão Resiliente e Distribuído (Marco 1.28)

## Overview
Transformar o pipeline de ingestão assíncrono em um motor distribuído de alta concorrência capaz de processar dezenas a centenas de documentos simultaneamente (50 a 300+ docs). A implementação elimina a contenção de concorrência no PostgreSQL através da decomposição DDD de `DocumentAggregate` (stream curto `doc-{id}` em $O(1)$), adota filas com entrega confiável *At-Least-Once* via Redis Streams (`XADD`/`XREADGROUP`/`XACK`/`XAUTOCLAIM`), barreira atômica de junção (*scatter-gather*), persistência de grafos com batching `UNWIND` no FalkorDB com pool dedicado de 64 threads, eliminação da escrita $N+1$ em `attached_documents`, e um Watchdog de auto-recuperação com lease atômico condicional e índice parcial.

---

## Architecture Decisions (Pós-Revisão Adversarial)

1. **Decomposição DDD Imediata (`DocumentAggregate`):**
   - Cada documento é promovido a Aggregate Root autônomo com seu próprio stream `doc-{document_id}` no `PostgresEventStore`.
   - Elimina 100% de contenção de concorrência e locks na tabela `event_streams` entre documentos distintos.
   - Stream curto (5 a 7 eventos durante toda a existência do documento), tornando o replay instantâneo (< 0,2ms em $O(1)$) e dispensando snapshots artificiais.
2. **CQRS Estrito e O(1) Relacional:**
   - `PostgresKnowledgeBaseRepository.save` passa a persistir exclusivamente a entidade raiz `knowledge_bases`, erradicando o laço $N+1$ sobre `attached_documents`.
   - A tabela `attached_documents` é atualizada exclusivamente pelo `KnowledgeBaseProjector`, reagindo aos eventos de domínio emitidos por `DocumentAggregate`.
3. **Redis Streams com Semântica At-Least-Once:**
   - Substituição de `BLPOP` destrutivo por Redis Streams (`XADD`, `XREADGROUP`, `XACK`, `XAUTOCLAIM`).
   - Tarefas permanecem no PEL (*Pending Entries List*) até o `XACK` ser enviado após gravação do checkpoint.
   - Workers caídos ou que sofrem OOM têm suas tarefas automaticamente recuperadas e redistribuídas via `XAUTOCLAIM`.
   - Payloads enxutos (*lean payloads*): o Redis trafega apenas ponteiros (`storage_path`), mantendo consumo de memória < 1MB e prevenindo disk thrashing no AOF.
4. **Barreira Atômica de Junção (Scatter-Gather Fork-Join):**
   - Coordenação de conclusão de chunks no Redis via contador atômico (`HINCRBY doc_barrier:{doc_id} completed_chunks 1`).
   - O worker que atinge o total de chunks consolida os subgrafos locais em disco e aciona a transição final do documento.
5. **Batching Cypher com `UNWIND` e ThreadPool Dedicado no FalkorDB:**
   - Inserção de múltiplos nós e arestas de uma só vez via `UNWIND $batch AS item MERGE ...`, reduzindo mais de 150 round-trips TCP por documento para apenas 2 requisições em lote.
   - `ThreadPoolExecutor(max_workers=64)` dedicado no adapter do FalkorDB para evitar esgotamento de threads no event loop do Python.
   - Labels estritas em todas as cláusulas `MATCH` (`:ParentChunk`, `:Entity`), eliminando *Full Graph Table Scans*.
6. **Watchdog de Auto-Recuperação com Lease Atômico:**
   - Índice parcial no PostgreSQL `idx_attached_documents_zombie_recovery` para varredura sem *Seq Scan*.
   - Heartbeat periódico de workers atualizando `updated_at = NOW()` a cada página/chunk.
   - Lease atômico no resgate: `UPDATE attached_documents SET status = 'RECOVERING' ... WHERE updated_at = $expected RETURNING id` para evitar falsos positivos e concorrência duplicada com workers lentos.
7. **Infraestrutura Tunada e Conexões Confiáveis:**
   - Redis com AOF persistente (`appendfsync everysec`).
   - PostgreSQL com buffers ampliados (512MB shared_buffers, 16MB work_mem, 200 max_connections).
   - Pools `asyncpg` (min 10, max 40) e `httpx` (200 conexões) dimensionados no FastAPI.
   - Rate Limiter protegido com clamp `tokens <= max_tpm` e jitter anti-thundering-herd.

---

## Dependency Graph

```
Docker Tuning (Postgres buffers, Redis AOF) & Partial Index
       │
       ├── Rate Limiter (Clamp & Jitter)
       │
       ├── FalkorDB Adapter (ThreadPool 64 + UNWIND Batching)
       │
       ▼
DocumentAggregate (doc-{id}) & Lean Domain Events
       │
       ├── PostgresDocumentRepository & KB Repository O(1)
       │
       ├── KnowledgeBaseProjector (Atualizações em attached_documents)
       │
       ▼
RedisStreamJobQueue (XADD, XREADGROUP, XACK, XAUTOCLAIM)
       │
       ├── Atomic Barrier (Scatter-Gather HINCRBY)
       │
       ▼
Workers Autônomos (OcrJobWorker, GraphJobWorker) & IngestionWatchdog
       │
       ▼
DocumentIngestionSagaCoordinator (Despacho via Streams)
       │
       ▼
FastAPI Lifespan & Container IoC (Pools 40/200, Graceful Shutdown)
       │
       ▼
Testes de Carga Concorrente Massiva (50-100 Docs) & Gate Pré-Commit
```

---

## Tasks

### Phase 1: Infraestrutura, Tuning e Otimizações de Banco
- [x] **Task 1: Tuning Docker Compose (Postgres, Redis AOF) e Índice Parcial de Recuperação**
- [x] **Task 2: Rate Limiter Hardening (Clamp & Jitter) e FalkorDB Adapter (ThreadPool 64 & UNWIND Batching)**

### Checkpoint 1: Infraestrutura e Adaptadores de Dados
- Containers operando com AOF e buffers ajustados. FalkorDB com batching UNWIND e pool dedicado. Rate limiter com clamp e jitter.

### Phase 2: Decomposição DDD (DocumentAggregate & CQRS Read Model O(1))
- [x] **Task 3: Criar `DocumentAggregate` e Eventos de Domínio Lean**
- [x] **Task 4: Criar `PostgresDocumentRepository` e Adaptar `KnowledgeBaseAggregate`**
- [x] **Task 5: Erradicar Escrita $N+1$ em `PostgresKnowledgeBaseRepository` e Sincronizar CQRS no `KnowledgeBaseProjector`**

### Checkpoint 2: Decomposição DDD e Event Sourcing O(1)
- `DocumentAggregate` persiste em `doc-{id}` em < 0,2ms sem concorrência entre docs. `kb_repo.save` executa em $O(1)$. Projector mantém `attached_documents` sincronizado.

### Phase 3: Fila Distribuída Redis Streams e Barreira Atômica
- [x] **Task 6: Implementar `RedisStreamJobQueue` com Semântica At-Least-Once**
- [x] **Task 7: Barreira Atômica de Junção (*Scatter-Gather Barrier*) e Payloads Enxutos**

### Checkpoint 3: Mensageria Distribuída e Barreira de Coordenação
- Redis Streams publica e consome com XREADGROUP/XACK. Payloads usam ponteiros de arquivo. Barreira atômica coordena múltiplos chunks sem race conditions.

### Phase 4: Workers Autônomos, Watchdog Blindado e Orquestração da Saga
- [x] **Task 8: Workers Autônomos (`OcrJobWorker` e `GraphJobWorker`) com Checkpoints Duráveis**
- [x] **Task 9: `IngestionWatchdog` com Lease Atômico Condicional e Heartbeats**
- [x] **Task 10: Atualizar `DocumentIngestionSagaCoordinator` para Despacho via Redis Streams**

### Checkpoint 4: Pipeline Completo Distribuído
- Workers processam tarefas de forma autônoma com entrega *At-Least-Once*. Watchdog recupera falhas sem falsos positivos.

### Phase 5: Lifespan FastAPI, IoC Container e Testes de Concorrência Massiva
- [x] **Task 11: Injeção de Dependências no Container IoC e Lifespan em `main.py`**
- [x] **Task 12: Bateria de Testes Unitários e de Concorrência Massiva (50-100 Docs Concorrentes)**
- [x] **Task 13: Gate Oficial Pré-Commit e Recuperação Operacional dos Documentos Zumbis**

### Checkpoint 5: Validação Final e Zero Documentos Zumbis
- `make pre-commit` 100% aprovado. Testes de concorrência massiva concluídos com sucesso. Todos os documentos chegam a `INDEXED`.

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Colisão de versão no Event Store sob centenas de documentos | Crítico | Decomposição em `DocumentAggregate`: cada documento grava em seu próprio stream `doc-{id}`, zerando colisões entre arquivos distintos. |
| Perda de tarefas por morte abrupta de workers (OOM/Restart) | Alto | Redis Streams com Consumer Groups (`XREADGROUP`/`XACK`). Tarefas não confirmadas são recuperadas via `XAUTOCLAIM`. |
| Saturação de memória no Redis por payloads de texto | Alto | *Lean Payloads*: tarefas trafegam exclusivamente ponteiros de armazenamento local (`storage_path`). |
| Starvation de threads no Python por chamadas Cypher do FalkorDB | Alto | Pool de threads dedicado (`ThreadPoolExecutor(max_workers=64)`) isolado para o driver FalkorDB. |
| Ingestão lenta por excesso de chamadas TCP ao FalkorDB | Médio | Batching atômico com Cypher `UNWIND`, reduzindo round-trips de centenas para 2 queries por documento. |
| Watchdog reprocessando documento em processamento legítimo | Alto | Heartbeat periódico atualizando `updated_at = NOW()` e lease atômico condicional (`UPDATE ... WHERE updated_at = $expected`). |
| Deadlock ou loop infinito no Rate Limiter | Médio | Clamp estrito `tokens <= max_tpm` e jitter aleatório de 10ms a 50ms para quebrar ondas (*thundering herd*). |
