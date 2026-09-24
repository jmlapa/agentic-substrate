# SPEC-resilient-distributed-ingestion-engine: Motor de Ingestão Resiliente e Distribuído (Escala: Centenas de Docs Concorrentes)

## 1. Contexto, Diagnóstico Real e Avaliação Adversarial

Uma reavaliação arquitetural adversarial profunda (conduzida sob a ótica de *Doubt-Driven Development*) auditou o pipeline de ingestão e as superfícies de persistência (`substrate_postgres`, `substrate_redis`, `substrate_falkordb`, `substrate_api`), avaliando o comportamento sob uma carga operacional de **dezenas a centenas de documentos submetidos em simultâneo (50 a 300+ documentos)**.

A auditoria revelou que a divisão anterior em duas fases (Fase 1 com "paliativos in-memory" e Fase 2 com "distribuição") introduzia **complexidade acidental descartável** e continha **pontos cegos críticos** que causariam falhas sistêmicas em produção.

---

## 2. Pontos Cegos, Zonas Cinzentas e Riscos Críticos Identificados

### 2.1 Ponto Cego 1: A Ilusão do Mutex In-Memory (`_kb_locks`)
- **A Falha:** `self._kb_locks: dict[UUID, asyncio.Lock]` é estritamente local a um único processo Python.
- **Cenário Multi-Worker / Multi-Container:** Em qualquer deploy com múltiplos workers Uvicorn (`uvicorn --workers 4`), múltiplos containers Docker (`substrate_api_1`, `substrate_api_2`) ou pods Kubernetes, os locks em memória são completamente ignorados entre processos. As colisões no PostgreSQL persistem inalteradas.
- **Cenário Single-Process sob 100 Documentos:** 100 documentos geram 500 mutações de agregado em fila sobre o mesmo lock. O 100º documento aguardaria mais de 18 segundos na fila serial. A validação CPU-bound de milhares de eventos Pydantic v2 congela o event loop principal, impedindo heartbeats e requisições HTTP.

### 2.2 Ponto Cego 2: Perda Irrecuperável de Tarefas com `BLPOP` (Violação do At-Least-Once)
- **A Falha:** `BLPOP` é uma operação destrutiva do Redis. No momento em que o comando retorna, o job é fisicamente excluído da fila.
- **Cenário de Crash / OOM:** Se um worker sofrer `SIGKILL` (redeploy), `OOMKilled` (muito comum em parsing pesado de PDF com OCR) ou exceção fatal de rede antes de persistir o checkpoint em disco: o job **desaparece para sempre**, sem Dead Letter Queue e sem retentativa.
- **Correção Mandatória:** Adoção de **Redis Streams (`XADD`, `XREADGROUP`, `XACK`, `XAUTOCLAIM`)** ou transferência atômica confiável via **`RPOPLPUSH` / `BLMOVE`** para fila de processamento intermediária, garantindo semântica *At-Least-Once*.

### 2.3 Ponto Cego 3: Saturação de Memória do Redis e I/O Thrashing do AOF
- **A Falha:** 300 documentos com 25 chunks cada geram 7.500 jobs de grafo. Cada job transportando o texto markdown integral do chunk (5KB a 16KB) inflaciona o Redis em mais de 100MB de strings brutas.
- **Amplificação no AOF:** Com `appendonly yes` e `appendfsync everysec`, milhares de pushes e pops com payloads volumosos degradam o subsistema de I/O em disco do container Redis.
- **Correção Mandatória:** **Eventos e Jobs Enxutos (*Lean Payloads*)**. O job transporta exclusivamente metadados e ponteiros de armazenamento (`storage_path`, `byte_offset`, `chunk_index`, `parent_id`), reduzindo o footprint de memória para < 1MB.

### 2.4 Zona Cinzenta 4: Ausência de Barreira de Junção (Scatter-Gather / Fork-Join)
- **A Falha:** Ao despachar 25 chunks de um documento para workers autônomos de grafo via Redis, quem decide que o 25º chunk concluiu a extração para consolidar o subgrafo e transicionar o documento para `mark_graph_extracted`?
- **Correção Mandatória:** **Barreira Atômica de Coordenação no Redis** (`HINCRBY doc_barrier:{doc_id} completed 1`). O worker que incrementa o contador e atinge `total_chunks` assume a responsabilidade de emitir o evento consolidado ou disparar a próxima etapa.

### 2.5 Ponto Cego 5: A Falácia do Snapshotting vs Fronteira de Agregado DDD
- **A Falha:** Criar infraestrutura de snapshotting (`aggregate_snapshots`) a cada 50 eventos para a `KnowledgeBaseAggregate` é um remendo complexo para tratar um agregador monolítico mal modelado.
- **Correção Mandatória:** **Decomposição Imediata de `DocumentAggregate`**. O ciclo de vida do documento é 100% independente dos demais. Com cada documento possuindo seu próprio stream (`doc-{document_id}`):
  - Cada stream possui apenas **5 a 7 eventos durante toda a sua existência**.
  - O replay de eventos consome **menos de 0,2 milissegundos** em $O(1)$.
  - **Zero colisões de versão no PostgreSQL** entre documentos distintos.
  - Dispensa completamente tabelas de snapshotting e locks em memória.

### 2.6 Ponto Cego 6: Watchdog com Seq Scan e Corrida Concorrente (Falsos Positivos)
- **A Falha:**
  1. Varredura a cada 2 minutos em `attached_documents` sem índice composto força *Seq Scan* (leitura sequencial de disco).
  2. Um documento grande (ex: 80 páginas) que leva 12 minutos legítimos para concluir o OCR seria considerado "zumbi" pelo watchdog, disparando um segundo worker concorrente que regrediria o status e corromperia arquivos em disco.
- **Correção Mandatória:**
  - Índice parcial: `CREATE INDEX idx_attached_documents_recovery ON attached_documents (status, updated_at) WHERE status IN ('UPLOADED', 'PARSED', 'CHUNKED');`
  - Heartbeat periódico de worker atualizando `updated_at = NOW()` a cada página/chunk processado.
  - Lease atômico no resgate: `UPDATE attached_documents SET status = 'RECOVERING', recovery_attempt = recovery_attempt + 1 WHERE id = $1 AND status = $expected AND updated_at = $expected RETURNING id;`

### 2.7 Ponto Cego 7: Esgotamento do `ThreadPoolExecutor` e 15.000 TCP Round-Trips no FalkorDB
- **A Falha:** `asyncio.to_thread` usa o threadpool global do Python (default teto 32 threads, ou 8 threads em 4 vCPUs). 100 documentos chamando FalkorDB saturam todas as threads do interpretador, travando leituras de disco e I/O.
- Além disso, gravar nós e arestas individualmente gera mais de **15.000 chamadas TCP sequenciais**, e consultas sem label explícita `MATCH (e {id: $id})` executam *Full Graph Scans*.
- **Correção Mandatória:**
  - `ThreadPoolExecutor` dedicado para o FalkorDB com 64 workers.
  - Gravação em lote via **Cypher `UNWIND $batch AS item MERGE ...`**, reduzindo de 150 para 2 comandos por documento.
  - Labels estritas em todas as cláusulas `MATCH`.

---

## 3. Decisão Arquitetural: Simplificação Radical (Unificação Direta)

Rejeita-se a divisão em Fase 1 e Fase 2. A implementação de `_kb_locks` temporários, retries complexos e snapshots em agregado monolítico representa **débito técnico intencional**.

O sistema implementará **diretamente a Arquitetura Unificada de Alta Escala**, que é mais simples, possui menos linhas de código acidental e resolve os problemas na raiz.

```
                             ┌─────────────────────────────────┐
                             │    POST /documents/attach       │
                             └────────────────┬────────────────┘
                                              │
                                   DocumentAttachedEvent
                                              ▼
                             ┌─────────────────────────────────┐
                             │  DocumentAggregate (doc-{id})   │
                             │   (Stream atômico: 5-7 evts)    │
                             └────────┬────────────────────────┘
                                      │
            ┌─────────────────────────┴────────────────────────┐
            │                                                  │
            ▼ (CQRS Read Model)                                ▼ (Task Dispatch)
┌───────────────────────────────┐              ┌───────────────────────────────┐
│    KnowledgeBaseProjector     │              │  Redis Streams Reliable Queue │
│ (Única fonte de escrita na    │              │  (XADD / XREADGROUP / XACK)   │
│  tabela attached_documents)   │              │  Stream: 'stream:doc:jobs'    │
└───────────────────────────────┘              └───────────────┬───────────────┘
                                                               │
                                         ┌─────────────────────┴─────────────────────┐
                                         ▼                                           ▼
                              ┌──────────────────────┐                   ┌──────────────────────┐
                              │    OcrJobWorker      │                   │   GraphJobWorker     │
                              │ (At-Least-Once + ACK)│                   │ (UNWIND Batch Cypher)│
                              └──────────┬───────────┘                   └──────────┬───────────┘
                                         │                                           │
                                         └─────────────────────┬─────────────────────┘
                                                               │
                                                               ▼
                                             ┌─────────────────────────────────┐
                                             │     Atomic Redis Barrier        │
                                             │   (HINCRBY doc_barrier:{id})    │
                                             └────────────────┬────────────────┘
                                                              │
                                            All Chunks Ready  ▼
                                             ┌─────────────────────────────────┐
                                             │ mark_graph_extracted & INDEXED  │
                                             └─────────────────────────────────┘
```

---

## 4. Especificação Técnica Detalhada

### 4.1 Decomposição DDD: `DocumentAggregate` Autônomo
- **Arquivo:** `src/modules/knowledge/domain/aggregates/document_aggregate.py`
- **Fronteira Transacional:** Cada documento possui seu próprio ID e grava no stream `doc-{document_id}` no `PostgresEventStore`.
- **Invariantes e Transições:**
  - `attach(kb_id, filename, file_size)` ➔ `DocumentAttachedEvent`
  - `mark_stored(storage_path)` ➔ `DocumentStoredEvent`
  - `mark_parsed(page_count, char_count)` ➔ `DocumentParsedEvent`
  - `mark_chunked(parent_count, child_count)` ➔ `DocumentChunkedEvent`
  - `mark_graph_extracted(node_count, edge_count)` ➔ `GraphExtractedFromDocumentEvent`
  - `mark_indexed()` ➔ `KnowledgeIndexedEvent`
  - `mark_failed(step, error_message)` ➔ `DocumentProcessingFailedEvent`
- **Resultado de Escala:** 300 documentos simultâneos gravam em 300 streams independentes. A cláusula `SELECT version FROM event_streams WHERE aggregate_id = $1 FOR UPDATE` bloqueia **apenas a linha daquele documento específico**. Conflito de concorrência entre documentos = **ZERO absoluto**.

### 4.2 CQRS Estrito: Desacoplamento de `PostgresKnowledgeBaseRepository`
- **Arquivo:** `src/modules/knowledge/infrastructure/adapters/postgres_knowledge_base_repository.py`
- O método `save(aggregate: KnowledgeBaseAggregate)` passa a gravar **exclusivamente** na tabela `knowledge_bases`.
- **Eliminação Total da Escrita $N+1$:** O laço `for doc_id, doc_info in aggregate.documents.items(): INSERT/UPDATE attached_documents` é completamente removido.
- A tabela `attached_documents` é atualizada **unicamente** pelo `KnowledgeBaseProjector`, reagindo aos eventos de domínio de forma assíncrona e desacoplada.

### 4.3 Redis Streams com Semântica At-Least-Once
- **Arquivo:** `src/kernel/infrastructure/redis_stream_job_queue.py`
- Substitui `LPUSH`/`BLPOP` pelo motor de streams do Redis:
  - **Publicação:** `XADD stream:doc:jobs * task_type <type> doc_id <id> payload_ref <path>`
  - **Consumo:** `XREADGROUP GROUP doc_workers worker_1 BLOCK 5000 COUNT 5 STREAMS stream:doc:jobs >`
  - **Confirmação:** `XACK stream:doc:jobs doc_workers <message_id>` após conclusão com sucesso e persistência de checkpoint.
  - **Auto-Claim de Falhas:** Supervisor executa periodicamente `XAUTOCLAIM stream:doc:jobs doc_workers worker_1 60000 0-0 COUNT 10` para reatribuir jobs de workers que morreram/sofreram OOM.
- **Paylod Enxuto:** O campo `payload_ref` aponta para o arquivo de checkpoint no disco local (`data/storage/kb-{id}/...`), garantindo que nenhum texto bruto trafegue pelo Redis.

### 4.4 Barreira Atômica de Junção (Scatter-Gather)
- **Mecanismo:** Ao fragmentar o documento em $N$ Parent Chunks, o coordinator registra no Redis:
  - `HSET doc_barrier:{doc_id} total_chunks N completed_chunks 0`
- Cada `GraphJobWorker` ao concluir a extração de um chunk grava o resultado intermediário em disco (`{partition}/chunks/graph_subgraphs/{chunk_id}.json`) e executa:
  - `HINCRBY doc_barrier:{doc_id} completed_chunks 1`
- O worker cujo incremento retornar exatamente $N$ assume a consolidação:
  1. Lê os subgrafos locais em disco.
  2. Executa a gravação em lote no FalkorDB.
  3. Despacha o comando para `DocumentAggregate.mark_graph_extracted`.
  4. Deleta a chave da barreira no Redis (`DEL doc_barrier:{doc_id}`).

### 4.5 Otimização de Escrita no FalkorDB (UNWIND Batching)
- **Arquivo:** `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`
- **Thread Pool Dedicado:** Criação de `self._executor = ThreadPoolExecutor(max_workers=64, thread_name_prefix="falkordb")`.
- **Batching de Chunks:**
  ```cypher
  UNWIND $chunks AS chunk
  MERGE (p:ParentChunk {id: chunk.id})
  SET p.content = chunk.content, p.kb_id = $kb_id, p.document_id = $doc_id
  WITH p, chunk
  UNWIND chunk.children AS child
  MERGE (c:ChildChunk {id: child.id})
  SET c.content = child.content, c.kb_id = $kb_id
  MERGE (p)-[:HAS_CHILD]->(c)
  ```
- **Labels Estritas em Relações:**
  ```cypher
  UNWIND $mentions AS m
  MATCH (p:ParentChunk {id: m.parent_id})
  MATCH (e:Entity {id: m.entity_id})
  MERGE (p)-[r:MENTIONS]->(e)
  ```
  Elimina 15.000 round-trips TCP para ~2 requisições em lote por documento.

### 4.6 Watchdog Blindado contra Falsos Positivos e Seq Scans
- **Arquivo:** `src/modules/knowledge/application/workers/ingestion_watchdog.py`
- **Índice no PostgreSQL:**
  ```sql
  CREATE INDEX IF NOT EXISTS idx_attached_documents_zombie_recovery
  ON attached_documents (status, updated_at)
  WHERE status IN ('UPLOADED', 'PARSED', 'CHUNKED');
  ```
- **Heartbeat:** Workers executam `UPDATE attached_documents SET updated_at = NOW() WHERE id = $1` a cada página/chunk concluído.
- **Lease Atômico no Resgate:** O Watchdog nunca invoca reprocessing sem antes vencer o lease:
  ```sql
  UPDATE attached_documents
  SET status = 'RECOVERING', updated_at = NOW(), recovery_attempt = recovery_attempt + 1
  WHERE id = $1 AND status = $expected_status AND updated_at = $expected_updated_at
  RETURNING id;
  ```
  Se retornar 0 linhas afetadas, outro worker ou processo já assumiu o documento.

### 4.7 Configuração de Hardware e Tuning
- **Docker Compose:**
  - PostgreSQL: `shared_buffers=512MB`, `work_mem=16MB`, `maintenance_work_mem=128MB`, `max_connections=200`.
  - Redis: `command: ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec", "--save", "60", "1000"]`.
  - Pool `asyncpg` no FastAPI: `min_size=10`, `max_size=40`, `timeout=20.0s`.
  - Pool `httpx`: `max_connections=200`, `max_keepalive_connections=50`.

---

## 5. Estrutura de Arquivos (Single Class per File)

```
src/
├── kernel/
│   └── infrastructure/
│       ├── async_token_bucket_limiter.py                  # Corrigido: clamp tpm e jitter anti-thundering-herd
│       ├── redis_stream_job_queue.py                      # Novo: Redis Streams com XADD/XREADGROUP/XACK/XAUTOCLAIM
│       └── app_settings.py                                # Configurações de pool, threads e concorrência
├── modules/
│   └── knowledge/
│       ├── domain/
│       │   ├── aggregates/
│       │   │   ├── knowledge_base_aggregate.py            # Desacoplado: retém apenas metadados e ontologia da KB
│       │   │   └── document_aggregate.py                  # Novo: Aggregate Root atômico por documento (stream doc-{id})
│       │   ├── events/
│       │   │   ├── document_attached_event.py             # Evento de anexo
│       │   │   ├── document_stored_event.py               # Evento de storage
│       │   │   ├── document_parsed_event.py               # Evento de parsing
│       │   │   ├── document_chunked_event.py              # Evento de chunking
│       │   │   ├── graph_extracted_from_document_event.py # Evento lean de grafo
│       │   │   ├── knowledge_indexed_event.py             # Evento lean de indexação
│       │   │   └── document_processing_failed_event.py    # Evento de falha explícita
│       │   └── interfaces/
│       │       └── i_stream_job_queue.py                  # Interface para filas em streaming
│       ├── application/
│       │   ├── sagas/
│       │   │   └── document_ingestion_saga_coordinator.py # Despacho via Redis Streams e barreira de junção
│       │   └── workers/
│       │       ├── ocr_job_worker.py                      # Worker At-Least-Once de OCR via Redis Streams
│       │       ├── graph_job_worker.py                    # Worker de Grafo com barreira atômica e UNWIND
│       │       └── ingestion_watchdog.py                  # Cron de auto-recuperação com lease atômico
│       └── infrastructure/
│           ├── adapters/
│           │   ├── postgres_knowledge_base_repository.py  # Erradicada escrita N+1 (grava só knowledge_bases em O(1))
│           │   ├── postgres_document_repository.py        # Repositório dedicado para DocumentAggregate
│           │   ├── falkordb_graph_store_adapter.py        # Otimizado: UNWIND batching e executor dedicado 64 threads
│           │   └── openrouter_client_factory.py           # Otimizado: pool httpx ampliado
│           └── projections/
│               └── knowledge_base_projector.py            # Atualiza attached_documents exclusivamente via eventos
└── api_gateway/
    ├── container.py                                       # Injeção de dependências atualizada
    └── main.py                                            # Lifespan: pools ampliados e inicialização de workers
```

---

## 6. Estratégia de Testes

1. **Testes Unitários:**
   - `test_document_aggregate_lifecycle.py`: Testar transições de estado completas de `DocumentAggregate` com validação de stream curto.
   - `test_redis_stream_queue_ack.py`: Testar publicação, leitura por grupo, ACK e reatribuição de jobs órfãos com `XAUTOCLAIM`.
   - `test_atomic_barrier.py`: Simular múltiplos workers incrementando a barreira concorrente e garantir que apenas o último worker dispara o evento de consolidação.
   - `test_token_bucket_clamp.py`: Validar ausência de loop infinito quando `estimated_tokens > max_tpm` e conferir jitter.
2. **Testes de Integração e Carga:**
   - `test_massive_concurrent_ingestion.py`: Submissão simultânea de **50 a 100 documentos reais** contra instâncias reais de PostgreSQL, Redis e FalkorDB.
   - **Critério de Aprovação:** 100% dos documentos atingem `INDEXED` sem nenhuma exceção `Concurrency conflict`, sem documentos zumbis e sem conexões orfãs.
   - `test_worker_crash_recovery.py`: Simular morte abrupta de worker no meio do parsing e validar que o Watchdog/XAUTOCLAIM reprocessa o documento a partir do checkpoint em disco sem re-cobrança de tokens.

---

## 7. Critérios de Sucesso Inegociáveis

1. **Zero Colisões sob Carga Paralela Massiva:** 100 documentos submetidos simultaneamente processam sem nenhum conflito de concorrência no PostgreSQL.
2. **Semântica At-Least-Once Comprovada:** Zero tarefas perdidas em quedas ou reinicializações de containers.
3. **Zero Documentos Zumbis:** Nenhum arquivo permanece estagnado por mais de 10 minutos sem ser detectado e recuperado pelo lease do Watchdog.
4. **Performance do FalkorDB:** Ingestão de grafos através de batching `UNWIND`, com taxa de escrita sustentada acima de 50 chunks/segundo sem estourar o thread pool.
5. **Gates de Qualidade 100% Verificados:** `make pre-commit` com zero erros de Mypy estrito e Ruff.
