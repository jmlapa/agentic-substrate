# Lista de Tarefas: Infraestrutura Local e Adaptadores de Produção (Marco 1.5)

## Fase 1: Docker Compose, Armazenamento Local e Parser

### Tarefa 1: Atualizar `docker-compose.yml` e Dependências do Projeto
**Descrição:** Atualizar o `docker/docker-compose.yml` para conter os serviços `postgres` (com `pgvector`), `falkordb` e `redis`, configurando variáveis de ambiente, portas e mapeamento de volumes locais na pasta `./data/`. Adicionar dependências necessárias (`markitdown`, `aiofiles`, `falkordb`) no `pyproject.toml`.
**Critérios de Aceite:**
- [ ] `docker/docker-compose.yml` atualizado com Postgres 16 (pgvector), FalkorDB latest e Redis 7.
- [ ] `pyproject.toml` atualizado com dependências estritas.
- [ ] Configuração do `.gitignore` para ignorar o diretório local `./data/`.
**Verificação:**
- [ ] `docker compose -f docker/docker-compose.yml config`
**Dependências:** Nenhuma
**Arquivos prováveis:**
- `docker/docker-compose.yml`
- `pyproject.toml`
- `.gitignore`
**Escopo estimado:** S (3 arquivos)

---

### Tarefa 2: Implementar `LocalFileSystemStorageAdapter`
**Descrição:** Implementar o adaptador de armazenamento local implementando `IObjectStorage`, permitindo leitura, escrita e geração de caminhos locais assíncronos usando `aiofiles`.
**Critérios de Aceite:**
- [ ] Arquivo `src/modules/knowledge/infrastructure/adapters/local_file_system_storage_adapter.py` criado isoladamente (Single Class per File).
- [ ] Métodos assíncronos: `put_object`, `get_object` e `generate_upload_url`.
- [ ] Testes unitários com diretório temporário cobrindo escrita, leitura e exceções.
**Verificação:**
- [ ] `pytest tests/unit/ -k test_local_file_system_storage`
**Dependências:** Tarefa 1
**Arquivos prováveis:**
- `src/modules/knowledge/infrastructure/adapters/local_file_system_storage_adapter.py`
- `src/modules/knowledge/infrastructure/adapters/__init__.py`
- `tests/unit/test_local_file_system_storage_adapter.py`
**Escopo estimado:** S (3 arquivos)

---

### Tarefa 3: Implementar `MarkItDownDocumentParser`
**Descrição:** Implementar o adaptador `MarkItDownDocumentParser` utilizando a biblioteca `markitdown` para converter PDF, DOCX, TXT e HTML para Markdown limpo em conformidade com o protocolo `IDocumentParser`.
**Critérios de Aceite:**
- [ ] Arquivo `src/modules/knowledge/infrastructure/adapters/markitdown_document_parser.py` criado isoladamente.
- [ ] Implementa `parse_to_markdown(raw_bytes, file_name, content_type)`.
- [ ] Testes unitários cobrindo conversão de texto e arquivos suportados.
**Verificação:**
- [ ] `pytest tests/unit/ -k test_markitdown_document_parser`
**Dependências:** Tarefa 1
**Arquivos prováveis:**
- `src/modules/knowledge/infrastructure/adapters/markitdown_document_parser.py`
- `src/modules/knowledge/infrastructure/adapters/__init__.py`
- `tests/unit/test_markitdown_document_parser.py`
**Escopo estimado:** S (3 arquivos)

---

## Checkpoint 1: Infraestrutura Base, Storage e Parser
- [ ] Containers sobem corretamente com `docker compose -f docker/docker-compose.yml up -d`.
- [ ] Testes de storage local e parser passando: `pytest tests/unit/ -k "storage or parser"`.
- [ ] Tipagem rigorosa com `mypy src`.

---

## Fase 2: Persistência Real (Postgres Event Store & PgVector Store)

### Tarefa 4: Implementar `PostgresEventStore`
**Descrição:** Implementar o `PostgresEventStore` no Kernel conectando via `asyncpg` / `SQLAlchemy Async`, persistindo fluxos de eventos append-only com verificação de concorrência otimista.
**Critérios de Aceite:**
- [ ] Arquivo `src/kernel/infrastructure/postgres_event_store.py` criado isoladamente.
- [ ] Tabela de eventos criada/inicializada com colunas de `aggregate_id`, `aggregate_type`, `event_type`, `event_data` (JSONB) e `version`.
- [ ] Testes unitários e de integração com mock/instância real de Postgres.
**Verificação:**
- [ ] `pytest tests/unit/ -k test_postgres_event_store`
**Dependências:** Tarefa 1
**Arquivos prováveis:**
- `src/kernel/infrastructure/postgres_event_store.py`
- `src/kernel/infrastructure/__init__.py`
- `tests/unit/test_postgres_event_store.py`
**Escopo estimado:** M (3 arquivos)

---

### Tarefa 5: Implementar `PgVectorStoreAdapter`
**Descrição:** Implementar o adaptador de busca e armazenamento vetorial `PgVectorStoreAdapter` no módulo `knowledge`, utilizando a extensão `pgvector` e índice HNSW com suporte a filtros por `kb_id`.
**Critérios de Aceite:**
- [ ] Arquivo `src/modules/knowledge/infrastructure/adapters/pgvector_store_adapter.py` criado isoladamente.
- [ ] Implementa `store_node_embeddings` e `search_similar_nodes`.
- [ ] Testes unitários com cálculos de distância de cosseno.
**Verificação:**
- [ ] `pytest tests/unit/ -k test_pgvector_store_adapter`
**Dependências:** Tarefa 4
**Arquivos prováveis:**
- `src/modules/knowledge/infrastructure/adapters/pgvector_store_adapter.py`
- `src/modules/knowledge/infrastructure/adapters/__init__.py`
- `tests/unit/test_pgvector_store_adapter.py`
**Escopo estimado:** M (3 arquivos)

---

## Checkpoint 2: Persistência Relacional, Event Store e Vetores
- [ ] Event Store e Vector Store operacionais no Postgres.
- [ ] Testes passando: `pytest tests/unit/ -k "postgres or pgvector"`.

---

## Fase 3: Grafo Real (FalkorDB) e Injeção de Dependências

### Tarefa 6: Implementar `FalkorDbGraphStoreAdapter`
**Descrição:** Implementar o adaptador `FalkorDbGraphStoreAdapter` no módulo `knowledge`, conectando ao FalkorDB via cliente assíncrono/OpenCypher para persistir nós, arestas e consultar subgrafos.
**Critérios de Aceite:**
- [ ] Arquivo `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py` criado isoladamente.
- [ ] Implementa `store_graph(kb_id, graph)` e `query_subgraph(kb_id, query, top_k)`.
- [ ] Testes unitários e de queries Cypher geradas.
**Verificação:**
- [ ] `pytest tests/unit/ -k test_falkordb_graph_store_adapter`
**Dependências:** Tarefa 1
**Arquivos prováveis:**
- `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`
- `src/modules/knowledge/infrastructure/adapters/__init__.py`
- `tests/unit/test_falkordb_graph_store_adapter.py`
**Escopo estimado:** M (3 arquivos)

---

### Tarefa 7: Atualizar Container de Injeção de Dependências (IoC)
**Descrição:** Atualizar `src/api_gateway/container.py` e `src/api_gateway/main.py` para instanciar os adaptadores reais quando configurados via variáveis de ambiente (`STORAGE_TYPE=local`, `GRAPH_STORE_TYPE=falkordb`, `VECTOR_STORE_TYPE=pgvector`, `EVENT_STORE_TYPE=postgres`).
**Critérios de Aceite:**
- [ ] Factory dinâmica no container respeitando as configurações de ambiente com fallback para in-memory em testes.
- [ ] Gerenciamento de ciclo de vida (startup/shutdown dos pools e conexões).
- [ ] Testes de integração da API com os novos adaptadores.
**Verificação:**
- [ ] `pytest tests/integration/`
**Dependências:** Tarefa 2, Tarefa 3, Tarefa 4, Tarefa 5, Tarefa 6
**Arquivos prováveis:**
- `src/api_gateway/container.py`
- `src/api_gateway/main.py`
- `tests/integration/test_api_gateway.py`
**Escopo estimado:** M (3-4 arquivos)

---

## Checkpoint Final: Validação de Qualidade
- [ ] `make pre-commit` (Ruff check, Ruff format, Mypy strict, Pytest com 100% de cobertura).
