# Tasks: Motor de Ingestão Resiliente e Distribuído (Marco 1.28)

## Phase 1: Infraestrutura, Tuning e Otimizações de Banco

### Task 1: Tuning Docker Compose (Postgres, Redis AOF) e Índice Parcial de Recuperação
**Description:** Configurar a persistência durável AOF no Redis e ampliar a alocação de recursos e buffers do PostgreSQL no Docker Compose. Criar migração/script para adicionar índice parcial em `attached_documents` para varredura de auto-recuperação sem *Seq Scan*.
**Acceptance criteria:**
- [x] Redis configurado com `command: ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec", "--save", "60", "1000"]` em `docker/docker-compose.yml` e `deploy/vm/docker-compose.yml`.
- [x] PostgreSQL configurado com buffers ampliados (`shared_buffers=512MB`, `work_mem=16MB`, `maintenance_work_mem=128MB`, `max_connections=200`, `checkpoint_completion_target=0.9`, `wal_buffers=16MB`).
- [x] Índice parcial `idx_attached_documents_zombie_recovery` criado em `attached_documents (status, updated_at) WHERE status IN ('UPLOADED', 'PARSED', 'CHUNKED')`.
**Verification:**
- [x] `docker compose -f docker/docker-compose.yml config` valida sintaxe do compose sem erros.
- [x] Conexão ao container Postgres executa `\d attached_documents` e lista o índice parcial.
- [ ] Conexão ao container Redis executa `CONFIG GET appendonly` e retorna `"yes"`.
**Dependencies:** None
**Files likely touched:**
- `docker/docker-compose.yml`
- `deploy/vm/docker-compose.yml`
- `src/kernel/infrastructure/database/migrations/` (ou script DDL)
**Estimated scope:** S (2-3 files)

---

### Task 2: Rate Limiter Hardening (Clamp & Jitter) e FalkorDB Adapter (ThreadPool 64 & UNWIND Batching)
**Description:** Corrigir risco de loop infinito no `AsyncTokenBucketLimiter` com clamp de tokens máximos e jitter anti-thundering-herd. Otimizar `FalkorDBGraphStoreAdapter` com `ThreadPoolExecutor(max_workers=64)` isolado e reescrever queries de inserção com Cypher `UNWIND $batch AS item MERGE ...` e labels estritas.
**Acceptance criteria:**
- [x] `AsyncTokenBucketLimiter` clampa tokens solicitados em `min(max(1, estimated_tokens), self._max_tpm)` e adiciona jitter de 10ms–50ms ao tempo de espera.
- [x] `FalkorDBGraphStoreAdapter` possui thread pool dedicado com 64 workers (`thread_name_prefix="falkordb"`).
- [x] Inserções de Parent Chunks, Child Chunks e menções usam batching `UNWIND` parametrizado.
- [x] Todas as cláusulas `MATCH` no FalkorDB possuem rótulos explícitos (`:ParentChunk`, `:Entity`).
**Verification:**
- [x] `poetry run pytest tests/unit/test_async_token_bucket_limiter.py -v` (ou teste unitário do limiter).
- [x] `poetry run pytest tests/unit/test_falkordb_graph_store_adapter.py -v` (ou teste de persistência em grafo).
**Dependencies:** None
**Files likely touched:**
- `src/kernel/infrastructure/async_token_bucket_limiter.py`
- `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`
- `tests/unit/test_async_token_bucket_limiter.py`
**Estimated scope:** M (3 files)

---

## Checkpoint 1: Infraestrutura e Adaptadores de Dados
- [x] Redis com AOF ativo e PostgreSQL com buffers tunados e índice parcial.
- [x] Rate Limiter com clamp e jitter verificados.
- [x] FalkorDB com batching UNWIND e pool dedicado de threads.

---

## Phase 2: Decomposição DDD (DocumentAggregate & CQRS Read Model O(1))

### Task 3: Criar `DocumentAggregate` e Eventos de Domínio Lean
**Description:** Implementar a entidade de domínio `DocumentAggregate` como Aggregate Root autônomo com stream próprio `doc-{document_id}` e eventos de domínio lean (armazenando ponteiros em vez de grafos JSON gigantes).
**Acceptance criteria:**
- [x] `DocumentAggregate` criado em `src/modules/knowledge/domain/aggregates/document_aggregate.py` respeitando *Single Class per File*.
- [x] Transições de estado atômicas: `attach`, `mark_stored`, `mark_parsed`, `mark_chunked`, `mark_graph_extracted`, `mark_indexed`, `mark_failed`.
- [x] Eventos de domínio criados em arquivos individuais: `DocumentAttachedEvent`, `DocumentStoredEvent`, `DocumentParsedEvent`, `DocumentChunkedEvent`, `GraphExtractedFromDocumentEvent`, `KnowledgeIndexedEvent`, `DocumentProcessingFailedEvent`.
- [x] Eventos não transportam JSONs gigantes de grafo; transportam contadores e `storage_path`.
**Verification:**
- [x] `poetry run pytest tests/modules/knowledge/domain/test_document_aggregate.py -v`
- [x] `poetry run mypy src/modules/knowledge/domain/aggregates/document_aggregate.py`
**Dependencies:** Task 1
**Files likely touched:**
- `src/modules/knowledge/domain/aggregates/document_aggregate.py`
- `src/modules/knowledge/domain/events/document_*_event.py` (eventos individuais)
- `tests/modules/knowledge/domain/test_document_aggregate.py`
**Estimated scope:** M (4-5 files)

---

### Task 4: Criar `PostgresDocumentRepository` e Adaptar `KnowledgeBaseAggregate`
**Description:** Implementar `PostgresDocumentRepository` para carregar e salvar `DocumentAggregate` via `PostgresEventStore` com chave `doc-{id}` em $O(1)$. Adaptar `KnowledgeBaseAggregate` para manter apenas metadados e configuração da base.
**Acceptance criteria:**
- [x] `PostgresDocumentRepository` criado em `src/modules/knowledge/infrastructure/adapters/postgres_document_repository.py`.
- [x] `load(document_id)` lê exclusivamente o stream `doc-{document_id}` (< 7 eventos).
- [x] `save(aggregate)` faz append no stream do documento via `PostgresEventStore`.
- [x] `KnowledgeBaseAggregate` foca em metadados da KB e delega ciclo de vida para `DocumentAggregate`.
**Verification:**
- [x] `poetry run pytest tests/modules/knowledge/infrastructure/test_postgres_document_repository.py -v`
- [x] `poetry run mypy src/modules/knowledge/infrastructure/adapters/postgres_document_repository.py`
**Dependencies:** Task 3
**Files likely touched:**
- `src/modules/knowledge/domain/interfaces/i_document_repository.py`
- `src/modules/knowledge/infrastructure/adapters/postgres_document_repository.py`
- `src/modules/knowledge/domain/aggregates/knowledge_base_aggregate.py`
- `tests/modules/knowledge/infrastructure/test_postgres_document_repository.py`
**Estimated scope:** M (4 files)

---

### Task 5: Erradicar Escrita $N+1$ em `PostgresKnowledgeBaseRepository` e Sincronizar CQRS no `KnowledgeBaseProjector`
**Description:** Modificar `PostgresKnowledgeBaseRepository.save` para salvar exclusivamente a tabela `knowledge_bases` em $O(1)$, eliminando o laço `for doc in aggregate.documents`. Atualizar `KnowledgeBaseProjector` para reagir aos eventos de `DocumentAggregate` e manter `attached_documents` 100% atualizado.
**Acceptance criteria:**
- [x] `PostgresKnowledgeBaseRepository.save` executa apenas 1 query `INSERT/UPDATE` em `knowledge_bases`.
- [x] Laço de escrita em `attached_documents` removido de `PostgresKnowledgeBaseRepository.save`.
- [x] `KnowledgeBaseProjector` manipula eventos de documento (`DocumentStoredEvent`, `DocumentParsedEvent`, `DocumentChunkedEvent`, etc.) e atualiza `attached_documents` de forma idempotente.
**Verification:**
- [x] `poetry run pytest tests/modules/knowledge/infrastructure/test_postgres_knowledge_base_repository.py -v`
- [x] `poetry run pytest tests/unit/test_knowledge_base_projector.py -v`
**Dependencies:** Task 4
**Files likely touched:**
- `src/modules/knowledge/infrastructure/adapters/postgres_knowledge_base_repository.py`
- `src/modules/knowledge/infrastructure/projections/knowledge_base_projector.py`
- `tests/modules/knowledge/infrastructure/test_postgres_knowledge_base_repository.py`
**Estimated scope:** M (3 files)

---

## Checkpoint 2: Decomposição DDD e Event Sourcing O(1)
- [x] `DocumentAggregate` persiste em stream atômico curto sem colisão entre documentos.
- [x] `PostgresKnowledgeBaseRepository.save` executa em $O(1)$ sem gerar $N$ updates concorrentes.
- [x] `KnowledgeBaseProjector` projeta os status em `attached_documents` via CQRS limpo.

---

## Phase 3: Fila Distribuída Redis Streams e Barreira Atômica

### Task 6: Implementar `RedisStreamJobQueue` com Semântica At-Least-Once
**Description:** Implementar adaptador `RedisStreamJobQueue` sobre `redis.asyncio` utilizando Redis Streams para garantir entrega confiável, recuperação de workers caídos via `XAUTOCLAIM` e confirmação atômica via `XACK`.
**Acceptance criteria:**
- [x] `IStreamJobQueue` criada em `src/modules/knowledge/domain/interfaces/i_stream_job_queue.py`.
- [x] `RedisStreamJobQueue` criada em `src/kernel/infrastructure/redis_stream_job_queue.py`.
- [x] Métodos: `publish_task` (`XADD`), `consume_tasks` (`XREADGROUP`), `ack_task` (`XACK`), `claim_stale_tasks` (`XAUTOCLAIM`).
- [x] Criação automática de consumer groups (`XGROUP CREATE ... MKSTREAM`).
**Verification:**
- [x] `poetry run pytest tests/kernel/infrastructure/test_redis_stream_job_queue.py -v`
- [x] `poetry run mypy src/kernel/infrastructure/redis_stream_job_queue.py`
**Dependencies:** Task 1
**Files likely touched:**
- `src/modules/knowledge/domain/interfaces/i_stream_job_queue.py`
- `src/kernel/infrastructure/redis_stream_job_queue.py`
- `tests/kernel/infrastructure/test_redis_stream_job_queue.py`
**Estimated scope:** M (3 files)

---

### Task 7: Barreira Atômica de Junção (*Scatter-Gather Barrier*) e Payloads Enxutos
**Description:** Implementar a barreira de junção atômica em Redis (`AtomicJobBarrier`) para coordenar a conclusão de múltiplos chunks paralelos de um documento, e estruturar os payloads enxutos de tarefas com ponteiros de storage.
**Acceptance criteria:**
- [x] `AtomicJobBarrier` criada em `src/kernel/infrastructure/atomic_job_barrier.py`.
- [x] `init_barrier(doc_id, total_chunks)` inicializa a contagem no Redis.
- [x] `increment_and_check(doc_id) -> bool` executa `HINCRBY` atômico e retorna `True` exclusivamente para o worker que conclui o último chunk.
- [x] Payloads de tarefas (`PageOcrJobPayload`, `ParentGraphJobPayload`) adaptados para referenciar `storage_path` em vez de texto bruto de 16KB.
**Verification:**
- [x] `poetry run pytest tests/kernel/infrastructure/test_atomic_job_barrier.py -v`
- [x] `poetry run mypy src/kernel/infrastructure/atomic_job_barrier.py`
**Dependencies:** Task 6
**Files likely touched:**
- `src/kernel/infrastructure/atomic_job_barrier.py`
- `src/modules/knowledge/domain/value_objects/page_ocr_job_payload.py`
- `src/modules/knowledge/domain/value_objects/parent_graph_job_payload.py`
- `tests/kernel/infrastructure/test_atomic_job_barrier.py`
**Estimated scope:** M (4 files)

---

## Checkpoint 3: Mensageria Distribuída e Barreira de Coordenação
- [x] Redis Streams opera com semântica At-Least-Once comprovada via testes.
- [x] Barreira atômica coordena múltiplos chunks sem condições de corrida.
- [x] Payloads trafegam ponteiros de disco sem inflar memória no Redis.

---

## Phase 4: Workers Autônomos, Watchdog Blindado e Orquestração da Saga

### Task 8: Workers Autônomos (`OcrJobWorker` e `GraphJobWorker`) com Checkpoints Duráveis
**Description:** Implementar workers assíncronos que consomem tarefas do Redis Streams via consumer groups, executam as operações pesadas (OCR com ToC Sintético e Extração de Grafo LLM com RateLimiter), salvam checkpoints duráveis em disco e enviam `XACK`.
**Acceptance criteria:**
- [x] `OcrJobWorker` criado em `src/modules/knowledge/application/workers/ocr_job_worker.py`.
- [x] `GraphJobWorker` criado em `src/modules/knowledge/application/workers/graph_job_worker.py`.
- [x] Cada worker consome com `XREADGROUP`, grava checkpoint local em `data/storage/kb-{id}/`, emite heartbeat (`updated_at = NOW()`) e executa `XACK`.
- [x] No último chunk da barreira atômica, o worker consolida os subgrafos e despacha persistência no FalkorDB e atualização no `DocumentAggregate`.
**Verification:**
- [x] `poetry run pytest tests/modules/knowledge/application/workers/test_ocr_job_worker.py -v`
- [x] `poetry run pytest tests/modules/knowledge/application/workers/test_graph_job_worker.py -v`
**Dependencies:** Tasks 2, 4, 7
**Files likely touched:**
- `src/modules/knowledge/application/workers/ocr_job_worker.py`
- `src/modules/knowledge/application/workers/graph_job_worker.py`
- `tests/modules/knowledge/application/workers/test_ocr_job_worker.py`
- `tests/modules/knowledge/application/workers/test_graph_job_worker.py`
**Estimated scope:** M (4 files)

---

### Task 9: `IngestionWatchdog` com Lease Atômico Condicional e Heartbeats
**Description:** Implementar o serviço de supervisão periódico (cron de 2 minutos) que detecta documentos estagnados em `UPLOADED`, `PARSED` ou `CHUNKED` há mais de 10 minutos, adquire lease atômico condicional e reprocessa a partir dos checkpoints existentes em disco sem custo de tokens.
**Acceptance criteria:**
- [x] `IngestionWatchdog` criado em `src/modules/knowledge/application/workers/ingestion_watchdog.py`.
- [x] Query otimizada usando o índice parcial em `attached_documents`.
- [x] Lease atômico condicional: `UPDATE attached_documents SET status = 'RECOVERING', recovery_attempt = recovery_attempt + 1 WHERE id = $1 AND status = $expected_status AND updated_at = $expected_updated_at RETURNING id`.
- [x] Reinvocação via `ReprocessDocumentUseCase` aproveitando checkpoints em disco ($0.00 em tokens adicionais).
**Verification:**
- [x] `poetry run pytest tests/modules/knowledge/application/workers/test_ingestion_watchdog.py -v`
- [x] `poetry run mypy src/modules/knowledge/application/workers/ingestion_watchdog.py`
**Dependencies:** Tasks 1, 8
**Files likely touched:**
- `src/modules/knowledge/application/workers/ingestion_watchdog.py`
- `tests/modules/knowledge/application/workers/test_ingestion_watchdog.py`
**Estimated scope:** S (2 files)

---

### Task 10: Atualizar `DocumentIngestionSagaCoordinator` para Despacho via Redis Streams
**Description:** Refatorar o coordenador da saga para operar com o novo `DocumentAggregate`, delegar tarefas de OCR e Grafo para o `RedisStreamJobQueue`, e eliminar tarefas em background soltas (`asyncio.create_task` volátil).
**Acceptance criteria:**
- [x] `DocumentIngestionSagaCoordinator` despacha tarefas para o stream `stream:jobs:graph`.
- [x] Carrega e muta `DocumentAggregate` (stream `doc-{id}` em $O(1)$) em vez de travar a `KnowledgeBaseAggregate` inteira.
- [x] Tratamento estrito de erros com registro explícito em `DocumentProcessingFailedEvent` (fim do silenciamento em `_record_failure_safely`).
**Verification:**
- [x] `poetry run pytest tests/modules/knowledge/application/test_document_ingestion_saga_concurrency.py -v`
- [x] `poetry run pytest tests/modules/knowledge/application/test_document_ingestion_saga_stream_dispatch.py -v`
- [x] `poetry run pytest tests/integration/test_document_ingestion_saga_coordinator.py -v`
**Dependencies:** Tasks 4, 6, 8
**Files likely touched:**
- `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`
- `tests/modules/knowledge/application/test_document_ingestion_saga_stream_dispatch.py`
**Estimated scope:** M (2-3 files)

---

## Checkpoint 4: Pipeline Completo Distribuído
- [x] Workers autônomos processam OCR e Grafo em streaming com entrega confiável.
- [x] Watchdog com lease atômico resgata documentos travados sem duplicação de execução.
- [x] Saga Coordinator despacha para streams e opera em $O(1)$ com `DocumentAggregate`.

---

## Phase 5: Lifespan FastAPI, IoC Container e Testes de Concorrência Massiva

### Task 11: Injeção de Dependências no Container IoC e Lifespan em `main.py`
**Description:** Configurar pools elásticos (`asyncpg` 10-40 conexões, `httpx` 200 conexões), registrar cliente Redis assíncrono, instanciar e gerenciar o ciclo de vida dos workers e do watchdog no `lifespan` do FastAPI.
**Acceptance criteria:**
- [x] `src/api_gateway/container.py` registra `RedisStreamJobQueue`, `PostgresDocumentRepository`, workers e watchdog.
- [x] `src/api_gateway/main.py` configura pool `asyncpg` com `min_size=10, max_size=40, timeout=20.0s`.
- [x] Inicialização dos workers em background no startup e cancelamento limpo (*graceful shutdown*) no shutdown do `lifespan`.
**Verification:**
- [x] `poetry run pytest tests/unit/api_gateway/test_container.py -v`
- [x] `poetry run mypy src/api_gateway/`
**Dependencies:** Tasks 8, 9, 10
**Files likely touched:**
- `src/api_gateway/container.py`
- `src/api_gateway/main.py`
- `tests/unit/api_gateway/test_container.py`
**Estimated scope:** M (3 files)

---

### Task 12: Bateria de Testes Unitários e de Concorrência Massiva (50-100 Docs Concorrentes)
**Description:** Criar e executar suíte de testes de estresse e concorrência massiva submetendo de 50 a 100 documentos simultaneamente contra o pipeline distribuído.
**Acceptance criteria:**
- [x] Teste de carga com 50+ documentos submetidos concorrentemente.
- [x] 100% dos documentos chegam a `INDEXED` sem exceções de concorrência ou conflito de versão.
- [x] Teste de simulação de queda de worker validando reatribuição via `XAUTOCLAIM` e reprocessamento a partir de checkpoints.
**Verification:**
- [x] `poetry run pytest tests/integration/test_massive_concurrent_ingestion.py -v`
**Dependencies:** Task 11
**Files likely touched:**
- `tests/integration/test_massive_concurrent_ingestion.py`
**Estimated scope:** S (1-2 files)

---

### Task 13: Gate Oficial Pré-Commit e Recuperação Operacional dos Documentos Zumbis
**Description:** Executar a bateria completa de qualidade oficial (`make pre-commit`) e aplicar a recuperação nos 12 documentos que estão atualmente estagnados no banco de dados local.
**Acceptance criteria:**
- [x] `make pre-commit` executado com 100% de aprovação (Mypy estrito, Ruff check & format, Pytest com cobertura).
- [x] Os 12 documentos zumbis no PostgreSQL local (`UPLOADED` e `CHUNKED`) são recuperados com sucesso para `INDEXED`.
**Verification:**
- [x] `make pre-commit` retorna exit code 0.
- [x] Consulta SQL no PostgreSQL confirma `SELECT status, count(*) FROM attached_documents GROUP BY status;` com 100% `INDEXED`.
**Dependencies:** Tasks 1 a 12
**Files likely touched:** None (apenas scripts/testes e gates)
**Estimated scope:** S (1 file)

---

## Checkpoint 5: Validação Final e Zero Documentos Zumbis
- [x] `make pre-commit` 100% aprovado.
- [x] Testes de concorrência massiva concluídos com sucesso.
- [x] Todos os documentos em produção atingem `INDEXED`.
