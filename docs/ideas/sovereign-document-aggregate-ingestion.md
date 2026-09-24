# Sovereign DocumentAggregate Ingestion Engine (Opção B)

## 1. Problem Statement
> **How Might We** arquitetar um motor de ingestão e processamento GraphRAG distribuído capaz de ingerir dezenas a centenas de documentos simultaneamente com **zero contenção de concorrência**, **isolamento atômico de falhas**, **replay O(1)** e **retomada cirúrgica de checkpoints com custo zero de tokens**?

---

## 2. Recommended Direction: Pure Sovereign Aggregate (CQRS Radical)

### 2.1 Por que o "DocumentAggregate Soberano" é a Resposta Definitiva (Análise de A1)
Na dúvida levantada sobre **"Qual modelo é melhor para manter rastreabilidade, tracings, auditoria e retomada de ingestão sem perda de etapas?"**:

A resposta técnica definitiva é o **CQRS Puro com `DocumentAggregate` Soberano (`doc-{id}`)**, **sem** registrar eventos de anexo concorrentes no stream da `KnowledgeBaseAggregate`.

#### Comparativo Técnico:
| Critério | Opção A (God Aggregate na KB) | Híbrido (Evento Leve na KB + Doc Stream) | Opção B Recomendada (DocumentAggregate Soberano) |
| :--- | :--- | :--- | :--- |
| **Colisões de Versão (Postgres)** | Crítico ($O(N^2)$ retries em lote de $N$ docs) | **Crítico no Attach** ($N$ anexos paralelos colidem na KB) | **Zero Colisões** ($N$ streams independentes gravando em paralelo) |
| **Throughput de Ingestão** | Serializado via Mutex/Backoff | Serializado na fase de Attach | **Paralelismo Máximo Nativo** do Postgres (I/O livre) |
| **Tracing e Rastreabilidade** | Caótico (1.000+ eventos intercalados de $N$ docs) | Dividido entre KB e Doc | **Perfeito e Cirúrgico** (`get_events(doc_id)` retorna exatamente a linha do tempo pura daquele doc) |
| **Auditoria e Governança** | Difícil isolar o histórico de um arquivo | Eventos parciais duplicados | **100% Imutável**: Quem enviou, quando parsed, chunks, tokens, grafos e indexação em ~6 eventos |
| **Retomada de Falhas (Resumption)** | Carrega centenas de eventos da KB toda | Replay rápido, mas risco de lock na KB | **Replay O(1) Instantâneo (< 2ms)**. Identifica o estado exato (`PARSED`, `CHUNKED`) e retoma do disco sem gastar 1 centavo de LLM |
| **Complexidade de Código** | Alta (locks, snapshots, mutexes) | Média-Alta (manter sincronia entre 2 streams) | **Mínima e Elegante** (cada agregado cuida de sua fronteira DDD) |

---

## 3. Zonas Cinzentas (Grey Areas) e Obstáculos Mapeados

Durante a auditoria adversarial aprofundada, identificamos 4 potenciais armadilhas e desenhamos suas soluções:

### ⚠️ Grey Area 1: Lost Updates no `DataSourceRunProjector`
- **Problema:** Quando 20 documentos terminam o processamento no mesmo segundo, todos emitem `DocumentKnowledgeIndexedEvent`. Atualmente, `DataSourceRunProjector` executa um read-modify-write (`run = await repo.get_by_id(); run.record_document_indexed(); await repo.save()`). Dois workers lendo `indexed_files = 5` gravam `6` simultaneamente, perdendo atualizações e impedindo a Run de atingir o status `COMPLETED`.
- **Mitigação:** Transformar a persistência da run em uma mutação atômica em nível de SQL:
  ```sql
  UPDATE knowledge_data_source_runs
  SET indexed_files_count = indexed_files_count + 1,
      status = CASE WHEN indexed_files_count + failed_files_count + 1 >= total_files_discovered THEN 'COMPLETED' ELSE status END,
      completed_at = CASE WHEN indexed_files_count + failed_files_count + 1 >= total_files_discovered THEN extract(epoch from now()) ELSE completed_at END
  WHERE id = $1
  RETURNING indexed_files_count, failed_files_count, total_files_discovered, status;
  ```

### ⚠️ Grey Area 2: FalkorDB ThreadPool Starvation & Write Contention
- **Problema:** O driver oficial do FalkorDB (`falkordb-py`) é síncrono e é invocado via `asyncio.to_thread()`. O Python possui um `ThreadPoolExecutor` padrão limitado a 32 threads. Se 100 chunks tentarem consolidar grafos ao mesmo tempo, as threads se esgotarão, causando starvation e timeouts de socket. Além disso, FalkorDB adquire lock de escrita por chave de grafo.
- **Mitigação:** Controlar a consolidação com um `asyncio.Semaphore(8)` dedicado por partição de grafo ou via fila assíncrona, garantindo que escritas no mesmo grafo sejam despachadas com concorrência ordenada e sem exaustão de threads do host.

### ⚠️ Grey Area 3: Esgotamento do Pool Postgres (`asyncpg`)
- **Problema:** Com 50 documentos executando OCR, chunking e extração paralela, se cada etapa abrir conexões independentes sem controle de semáforo global, o pool default de 20 conexões do `asyncpg` pode estourar (`asyncpg.exceptions.TooManyConnectionsError`).
- **Mitigação:** Manter a persistência de eventos pontual (abre conexão, faz append, fecha/devolve ao pool). Operações de longa duração (LLM, OCR, Chunking) **nunca** seguram conexões do banco de dados.

### ⚠️ Grey Area 4: Exclusão em Cascata e Jobs Órfãos
- **Problema:** Se o usuário excluir ou arquivar uma KB enquanto 50 documentos estiverem no meio da extração LLM, jobs caros continuarão rodando em background consumindo créditos.
- **Mitigação:** Validação de ciclo de vida pré-LLM: os workers e a Saga verificam se a KB ainda está ativa (`status != 'ARCHIVED'`). Caso tenha sido arquivada, o processamento aborta de imediato descartando o trabalho subsequente.

---

## 4. Trade-offs Explícitos

| O que Ganhamos (Gains) | O que Abrimos Mão (Trade-offs Aceitos) |
| :--- | :--- |
| **Concorrência Ilimitada:** Zero contenção entre documentos no Event Store. | **Consistência Eventual na KB:** A lista de documentos da KB reside na projeção read-model (`attached_documents`), e não em uma lista in-memory dentro do `KnowledgeBaseAggregate`. |
| **Replay Ultrarrápido:** Agregados de documentos têm ~6 eventos (carregam em < 2ms). | **Dois Agregados no Domínio:** Em vez de um agregado monolítico, temos `KnowledgeBaseAggregate` e `DocumentAggregate`. |
| **Retomada Cirúrgica:** Recuperação de falha granular documento a documento. | **Clean Break (Corte Seco):** KBs e documentos legados incompatíveis são descartados (autorizado pelo usuário). |

---

## 5. Key Assumptions to Validate
- [ ] O stream `doc-{id}` no `PostgresEventStore` persiste e recupera eventos isoladamente sem requerer chaves estrangeiras relacionais prévias.
- [ ] O `KnowledgeBaseProjector` já atualiza a tabela `attached_documents` com base nos eventos de `DocumentAggregate` (validado no código: linhas 159-203).
- [ ] O `AttachAndStoreDocumentUseCase` não precisa mutar `KnowledgeBaseAggregate`, apenas validar a existência da KB e instanciar `DocumentAggregate`.
- [ ] Um lote de 14 documentos sincronizados simultaneamente conclui todas as etapas sem emitir um único `Concurrency conflict`.

---

## 6. MVP Scope (Clean Break Implementation)
1. **`AttachAndStoreDocumentUseCase`**:
   - Valida existência da KB (leitura rápida).
   - Cria `DocumentAggregate.create(...)` e executa upload no storage.
   - Salva via `PostgresDocumentRepository` e publica no `EventBus`.
   - Zero mutações em `KnowledgeBaseAggregate`.
2. **`DocumentIngestionSagaCoordinator`**:
   - Elimina lógica de fallback (`_mutate_document_or_kb` e locks de KB).
   - Opera 100% sobre `_document_repo.get_by_id(event.document_id)`.
   - Transiciona o estado no agregado do documento e publica eventos do documento.
3. **`DataSourceRunProjector` / Repositório**:
   - Ajusta atualização de progresso para operação atômica em SQL, prevenindo lost updates.
4. **Limpeza de Base (Clean Slate)**:
   - Limpa tabelas de dados/KBs de teste conforme solicitação do usuário.

---

## 7. Not Doing (and Why)
- **Não faremos Lock Distribuído no Redis para Agregados**: Inútil e custoso quando cada documento possui seu próprio stream isolado.
- **Não faremos Snapshotting de Agregado de Documento**: Como cada documento possui apenas ~6 eventos em todo o seu ciclo de vida, o replay leva < 2ms, tornando snapshots uma complexidade desnecessária.
- **Não manteremos retrocompatibilidade com KBs antigas**: O usuário optou explicitamente pelo corte seco (clean break).
