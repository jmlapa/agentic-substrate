# Task List: Google Drive Folder Data Source & Blue/Green Ingestion (Marco 1.25)

> **Regra de ouro:** Single Class per File. Implement → Test → Verify (passing) → Commit.
> Cada tarefa é atômica (1 a 5 arquivos), com critérios de aceitação testáveis e verificação explícita via pytest/mypy/ruff.

---

## Tasks

### Task 1: Criar Value Objects de Domínio do DataSource

**Description:** Cria os Value Objects e Enums necessários para tipagem estrita de tipos de fontes de dados, estados de sincronização, estados de execução, configuração de pastas do Google Drive e lotes de alteração descobertos.

**Acceptance criteria:**
- [x] `DataSourceType` (Enum com `GOOGLE_DRIVE_FOLDER`, `LOCAL_DIRECTORY`) criado em arquivo próprio.
- [x] `DataSourceStatus` (Enum com `IDLE`, `SYNCING`, `FAILED`, `DISABLED`) criado em arquivo próprio.
- [x] `DataSourceRunStatus` (Enum com `EXTRACTING`, `INGESTING`, `COMPLETED`, `PARTIALLY_FAILED`, `FAILED`) criado em arquivo próprio.
- [x] `GoogleDriveFolderConfig` (Value Object validado com `folder_id`, `recursive`, `baseline_days`, `include_mime_types`) criado em arquivo próprio.
- [x] `DiscoveredDocumentItem` e `DataSourceChangesBatch` criados em arquivos próprios.
- [x] `src/modules/knowledge/domain/value_objects/__init__.py` exporta todos os novos VOs.

**Verification:**
- [x] `uv run mypy --strict src/modules/knowledge/domain/value_objects/`
- [x] `uv run ruff check src/modules/knowledge/domain/value_objects/`

**Dependencies:** None

**Files likely touched:**
- `src/modules/knowledge/domain/value_objects/data_source_type.py`
- `src/modules/knowledge/domain/value_objects/data_source_status.py`
- `src/modules/knowledge/domain/value_objects/data_source_run_status.py`
- `src/modules/knowledge/domain/value_objects/google_drive_folder_config.py`
- `src/modules/knowledge/domain/value_objects/discovered_document_item.py`
- `src/modules/knowledge/domain/value_objects/data_source_changes_batch.py`
- `src/modules/knowledge/domain/value_objects/__init__.py`

**Estimated scope:** Medium (5-6 arquivos pequenos no padrão 1 classe por arquivo)

---

### Task 2: Criar Entidades de Domínio, Eventos e Protocols (Interfaces)

**Description:** Implementa as entidades de negócio puras `DataSource` e `DataSourceRun`, os eventos de domínio do ciclo de vida e os protocolos de interface para conectores e repositórios.

**Acceptance criteria:**
- [x] `DataSource` (entidade com `id`, `kb_id`, `name`, `type`, `status`, `cursor`, `config`, métodos de transição de estado) criada em arquivo próprio.
- [x] `DataSourceRun` (entidade que registra `sync_run_id`, `total_files`, `indexed_count`, `failed_count`, `failure_summary`) criada em arquivo próprio.
- [x] Eventos de domínio criados em arquivos próprios: `DataSourceCreatedEvent`, `DataSourceSyncStartedEvent`, `DataSourceSyncCompletedEvent`, `DataSourceSyncFailedEvent`, `DataSourceRunCompletedEvent`.
- [x] Interfaces/Protocols criados: `IDataSourceConnector`, `IDataSourceConnectorRegistry`, `IDataSourceRepository`, `IDataSourceRunRepository`.
- [x] Teste unitário cobrindo criação e transições das entidades em `tests/unit/test_data_source_domain.py`.

**Verification:**
- [x] `uv run pytest tests/unit/test_data_source_domain.py -v`
- [x] `uv run mypy --strict src/modules/knowledge/domain/`

**Dependencies:** Task 1

**Files likely touched:**
- `src/modules/knowledge/domain/entities/data_source.py`
- `src/modules/knowledge/domain/entities/data_source_run.py`
- `src/modules/knowledge/domain/interfaces/i_data_source_connector.py`
- `src/modules/knowledge/domain/interfaces/i_data_source_repository.py`
- `src/modules/knowledge/domain/interfaces/i_data_source_run_repository.py`
- `tests/unit/test_data_source_domain.py`

**Estimated scope:** Medium (5 arquivos)

---

### Checkpoint 1: Domain Primitives & Invariants
- [x] Todos os Value Objects e Entidades de Domínio tipados com Mypy strict.
- [x] Testes unitários do domínio passando com 100% de sucesso.
- [x] Zero dependências de SDKs externos na camada de domínio.

---

### Task 3: Criar Migração do Banco Relacional (PostgreSQL)

**Description:** Cria a migração Alembic para adicionar as tabelas `knowledge_data_sources` e `knowledge_data_source_runs` com chaves estrangeiras, índices e campos JSONB no PostgreSQL.

**Acceptance criteria:**
- [x] Arquivo de migração `migrations/versions/0008_create_knowledge_data_sources.py` criado.
- [x] Tabela `knowledge_data_sources` possui chave estrangeira `ON DELETE CASCADE` para `knowledge_bases(id)`.
- [x] Tabela `knowledge_data_source_runs` possui chave estrangeira para `knowledge_data_sources(id)`.
- [x] Índices criados para `kb_id`, `data_source_id` e `status`.

**Verification:**
- [x] `uv run ruff check migrations/versions/0008_create_knowledge_data_sources.py`

**Dependencies:** Task 2

**Files likely touched:**
- `alembic/versions/0007_create_knowledge_data_sources.py`

**Estimated scope:** Small (1 arquivo)

---

### Task 4: Implementar Repositórios Relacionais (PostgreSQL e In-Memory)

**Description:** Implementa as classes de repositório para `DataSource` e `DataSourceRun`, fornecendo tanto as implementações de produção no PostgreSQL quanto as implementações In-Memory de alta fidelidade para testes unitários isolados.

**Acceptance criteria:**
- [x] `InMemoryDataSourceRepository` implementa `IDataSourceRepository`.
- [x] `InMemoryDataSourceRunRepository` implementa `IDataSourceRunRepository`.
- [x] `PostgresDataSourceRepository` implementa operações CRUD no PostgreSQL via asyncpg/SQLAlchemy.
- [x] `PostgresDataSourceRunRepository` implementa operações no PostgreSQL.
- [x] Testes unitários cobrindo todos os métodos de repositório em `tests/unit/test_data_source_repositories.py`.

**Verification:**
- [x] `uv run pytest tests/unit/test_data_source_repositories.py -v`
- [x] `uv run mypy --strict src/modules/knowledge/infrastructure/adapters/`

**Dependencies:** Task 3

**Files likely touched:**
- `src/modules/knowledge/infrastructure/repositories/in_memory_data_source_repository.py`
- `src/modules/knowledge/infrastructure/repositories/in_memory_data_source_run_repository.py`
- `src/modules/knowledge/infrastructure/repositories/postgres_data_source_repository.py`
- `src/modules/knowledge/infrastructure/repositories/postgres_data_source_run_repository.py`
- `tests/unit/test_data_source_repositories.py`

**Estimated scope:** Medium (5 arquivos)

---

### Checkpoint 2: Persistence Layer
- [x] Tabelas migradas e acessíveis via repositórios.
- [x] Repositórios In-Memory e Postgres compatíveis com a mesma interface estrita.
- [x] Testes de persistência passando.

---

### Task 5: Implementar Connector Registry e In-Memory Connector Adapter

**Description:** Implementa o `DataSourceConnectorRegistry` para resolução polimórfica de conectores baseada em `DataSourceType`, e cria o `InMemoryDataSourceConnector` para simular descoberta e download de arquivos em testes.

**Acceptance criteria:**
- [x] `InMemoryDataSourceConnector` implementa `IDataSourceConnector` com capacidade de configurar arquivos mock e deltas.
- [x] `DataSourceConnectorRegistry` implementa `IDataSourceConnectorRegistry` permitindo registrar e recuperar adaptadores.
- [x] Teste unitário validando o registro e resolução em `tests/unit/test_data_source_connector_registry.py`.

**Verification:**
- [x] `uv run pytest tests/unit/test_data_source_connector_registry.py -v`
- [x] `uv run mypy --strict src/modules/knowledge/infrastructure/adapters/`

**Dependencies:** Task 2

**Files likely touched:**
- `src/modules/knowledge/infrastructure/adapters/in_memory_data_source_connector.py`
- `src/modules/knowledge/infrastructure/adapters/data_source_connector_registry.py`
- `tests/unit/test_data_source_connector_registry.py`

**Estimated scope:** Small (3 arquivos)

---

### Task 6: Implementar Adaptador Concreto `GoogleDriveFolderConnector`

**Description:** Implementa o adaptador especialista `GoogleDriveFolderConnector` em `infrastructure/adapters/google_drive/`, consumindo a Google Drive API v3 de forma assíncrona, convertendo Google Docs nativos para Markdown/texto e baixando binários com streaming.

**Acceptance criteria:**
- [x] Suporte a autenticação por Service Account GCP.
- [x] `fetch_changes()` consulta `files.list` (baseline) ou `changes.list` (delta) filtrando por `parents in folder_id`.
- [x] `download_document()` executa `files.export` para Google Docs (`text/plain`) e `files.get(alt='media')` para binários (PDF, áudio).
- [x] Tratamento gracioso de erros de rede e rate limits do Google.
- [x] Testes unitários com mocks da API do Google em `tests/unit/test_google_drive_folder_connector.py`.

**Verification:**
- [x] `uv run pytest tests/unit/test_google_drive_folder_connector.py -v`
- [x] `uv run mypy --strict src/modules/knowledge/infrastructure/adapters/google_drive/`

**Dependencies:** Task 5

**Files likely touched:**
- `src/modules/knowledge/infrastructure/adapters/google_drive/google_drive_folder_connector.py`
- `src/modules/knowledge/infrastructure/adapters/google_drive/__init__.py`
- `tests/unit/test_google_drive_folder_connector.py`

**Estimated scope:** Small/Medium (3 arquivos)

---

### Checkpoint 3: Connectors & Adapters
- [x] GoogleDriveFolderConnector capaz de listar alterações e baixar arquivos convertidos.
- [x] InMemoryDataSourceConnector pronto para uso nas suites de teste dos casos de uso.
- [x] Tipagem Mypy 100% estrita.

---

### Task 7: Implementar Casos de Uso de Gerenciamento do DataSource

**Description:** Implementa os Use Cases para criação, listagem, remoção e consulta de execuções (runs) de DataSources, seguindo estritamente a convenção Single Class per File com DTOs Request/Response e `Result[T, DomainError]`.

**Acceptance criteria:**
- [x] `CreateDataSourceUseCase` valida existência da KB e unicidade do conector.
- [x] `ListDataSourcesUseCase` lista os conectores associados a uma KB.
- [x] `ListDataSourceRunsUseCase` lista o histórico de execuções de um conector.
- [x] `DeleteDataSourceUseCase` remove a entidade com segurança.
- [x] Testes unitários para todos os casos de uso em `tests/unit/test_manage_data_source_use_cases.py`.

**Verification:**
- [x] `uv run pytest tests/unit/test_manage_data_source_use_cases.py -v`
- [x] `uv run mypy --strict src/modules/knowledge/application/use_cases/`

**Dependencies:** Task 4, Task 5

**Files likely touched:**
- `src/modules/knowledge/application/use_cases/create_data_source/create_data_source_use_case.py`
- `src/modules/knowledge/application/use_cases/list_data_sources/list_data_sources_use_case.py`
- `src/modules/knowledge/application/use_cases/list_data_source_runs/list_data_source_runs_use_case.py`
- `src/modules/knowledge/application/use_cases/delete_data_source/delete_data_source_use_case.py`
- `tests/unit/test_manage_data_source_use_cases.py`

**Estimated scope:** Medium (5 arquivos)

---

### Task 8: Implementar `SyncDataSourceUseCase` com Bounded Concurrency Worker

**Description:** Implementa o caso de uso de sincronização assíncrona, orquestrando a descoberta de metadados, controle de vazão via semáforo (`asyncio.Semaphore(max_concurrency=2)`), criação da `DataSourceRun` e handoff imediato para `AttachAndStoreDocumentUseCase` com carimbo de `sync_run_id`.

**Acceptance criteria:**
- [x] Cria e persiste a entidade `DataSourceRun` com status `EXTRACTING`.
- [x] Consulta `fetch_changes()` no conector resolvido pelo registry.
- [x] Loop de extração controlado por semáforo de concorrência liberando a memória RAM após cada entrega ao storage.
- [x] Carimba `source_metadata={"data_source_id": id, "sync_run_id": run.id, "version_hash": hash}` em cada documento.
- [x] Identifica se o arquivo já existia com outro hash e define `replaces_doc_id = old_doc_id`.
- [x] Atualiza a `DataSourceRun` para `INGESTING` e avança o cursor do `DataSource` para o próximo token.
- [x] Testes unitários com simulação de 5 arquivos mock em `tests/unit/test_sync_data_source_use_case.py`.

**Verification:**
- [x] `uv run pytest tests/unit/test_sync_data_source_use_case.py -v`
- [x] `uv run mypy --strict src/modules/knowledge/application/use_cases/sync_data_source/`

**Dependencies:** Tasks 5, 6 e 7

**Files likely touched:**
- `src/modules/knowledge/application/use_cases/sync_data_source/sync_data_source_request.py`
- `src/modules/knowledge/application/use_cases/sync_data_source/sync_data_source_response.py`
- `src/modules/knowledge/application/use_cases/sync_data_source/sync_data_source_use_case.py`
- `src/modules/knowledge/application/use_cases/sync_data_source/__init__.py`
- `tests/unit/test_sync_data_source_use_case.py`

**Estimated scope:** Medium (5 arquivos)

---

### Task 9: Implementar Handlers Reativos: Blue/Green Swap e DataSourceRunProjector

**Description:** Cria os listeners de eventos desacoplados: `BlueGreenDocumentSwapHandler` para expurgar versões anteriores após indexação da nova, e `DataSourceRunProjector` para atualizar o progresso e finalizar as runs conforme os documentos são processados pelas Sagas.

**Acceptance criteria:**
- [x] `BlueGreenDocumentSwapHandler` escuta `DocumentIndexedEvent`: se `replaces_doc_id` estiver presente, invoca `DeleteDocumentUseCase(kb_id, replaces_doc_id)`.
- [x] Se `replaces_doc_id` for `None`, o handler é No-Op.
- [x] `DataSourceRunProjector` escuta `DocumentIndexedEvent` e incrementa `indexed_files_count` na run correspondente via `sync_run_id`.
- [x] `DataSourceRunProjector` escuta `DocumentIngestionFailedEvent` e incrementa `failed_files_count`, anexando o erro no `failure_summary`.
- [x] Ao atingir `total_files`, a run é finalizada com o status correto (`COMPLETED`, `PARTIALLY_FAILED` ou `FAILED`).
- [x] Testes unitários em `tests/unit/test_data_source_handlers.py`.

**Verification:**
- [x] `uv run pytest tests/unit/test_data_source_handlers.py -v`
- [x] `uv run mypy --strict src/modules/knowledge/application/handlers/`

**Dependencies:** Task 8

**Files likely touched:**
- `src/modules/knowledge/application/handlers/blue_green_document_swap_handler.py`
- `src/modules/knowledge/application/handlers/data_source_run_projector.py`
- `src/modules/knowledge/application/handlers/__init__.py`
- `tests/unit/test_data_source_handlers.py`

**Estimated scope:** Medium (4 arquivos)

---

### Checkpoint 4: Core Application Logic & Reactivity
- [x] Sync worker executando streaming $O(1)$ sem bloquear a API.
- [x] Blue/Green swap atômico funcionando via eventos sem downtime.
- [x] DataSourceRun rastreando métricas com fidelidade de ponta a ponta.

---

### Task 10: Implementar DTOs e Controller na API Gateway

**Description:** Cria os DTOs isolados de request/response e o `DataSourceController` na camada `api_gateway`, expondo endpoints REST para CRUD e disparo de sincronização assíncrona com resposta imediata `202 Accepted`.

**Acceptance criteria:**
- [ ] DTOs Pydantic v2 criados: `CreateDataSourceDTO`, `DataSourceResponseDTO`, `DataSourceRunResponseDTO`, `SyncDataSourceResponseDTO`.
- [ ] Controller expõe rotas:
  - `POST /api/v1/knowledge-bases/{kb_id}/data-sources` (Criação)
  - `GET /api/v1/knowledge-bases/{kb_id}/data-sources` (Listagem)
  - `DELETE /api/v1/knowledge-bases/{kb_id}/data-sources/{id}` (Exclusão)
  - `POST /api/v1/knowledge-bases/{kb_id}/data-sources/{id}/sync` (Disparo do Sync com resposta `202 Accepted`)
  - `GET /api/v1/knowledge-bases/{kb_id}/data-sources/{id}/runs` (Histórico de Execuções)
- [ ] Testes unitários do controller com FastAPI `TestClient` em `tests/unit/api_gateway/test_data_source_controller.py`.

**Verification:**
- [ ] `uv run pytest tests/unit/api_gateway/test_data_source_controller.py -v`
- [ ] `uv run mypy --strict src/api_gateway/`

**Dependencies:** Tasks 7, 8 e 9

**Files likely touched:**
- `src/api_gateway/dtos/create_data_source_dto.py`
- `src/api_gateway/dtos/data_source_response_dto.py`
- `src/api_gateway/dtos/data_source_run_response_dto.py`
- `src/api_gateway/dtos/sync_data_source_response_dto.py`
- `src/api_gateway/controllers/data_source_controller.py`
- `tests/unit/api_gateway/test_data_source_controller.py`

**Estimated scope:** Medium (5-6 arquivos)

---

### Task 11: Fazer o Wiring das Dependências no IoC Container e `main.py`

**Description:** Registra as novas instâncias de repositórios, conectores, use cases e event handlers no container de injeção de dependências (`container.py`) e inclui o novo controller no roteamento da aplicação em `main.py`.

**Acceptance criteria:**
- [ ] `src/api_gateway/container.py` instancia `PostgresDataSourceRepository`, `PostgresDataSourceRunRepository`, `DataSourceConnectorRegistry` e os novos Use Cases.
- [ ] `BlueGreenDocumentSwapHandler` e `DataSourceRunProjector` registrados no `EventBus` durante o startup.
- [ ] Router de data sources incluído no FastAPI em `src/api_gateway/main.py`.

**Verification:**
- [ ] `uv run mypy --strict src/api_gateway/container.py src/api_gateway/main.py`
- [ ] `uv run ruff check src/api_gateway/`

**Dependencies:** Task 10

**Files likely touched:**
- `src/api_gateway/container.py`
- `src/api_gateway/main.py`

**Estimated scope:** Small (2 arquivos)

---

### Task 12: Testes de Integração End-to-End e Verificação de Quality Gates

**Description:** Implementa testes de integração ponta a ponta validando o fluxo completo (Criação de DataSource ➔ Disparo de Sync ➔ Ingestão ➔ Swap de Versão no FalkorDB ➔ Rastreabilidade na Run) e executa o gate oficial `make pre-commit`.

**Acceptance criteria:**
- [ ] `tests/integration/test_data_source_api_gateway.py` valida todas as rotas HTTP do conector.
- [ ] `tests/integration/test_e2e_data_source_sync_and_swap.py` valida o fluxo completo com simulação de nova versão de documento e verificação de expurgo no FalkorDB.
- [ ] Execução com 100% de sucesso de `make pre-commit` (Ruff linter/formatter, Mypy strict mode sem warnings, Pytest com cobertura total).

**Verification:**
- [ ] `make pre-commit`

**Dependencies:** Task 11

**Files likely touched:**
- `tests/integration/test_data_source_api_gateway.py`
- `tests/integration/test_e2e_data_source_sync_and_swap.py`

**Estimated scope:** Small/Medium (2 arquivos de teste robustos)

---

### Checkpoint 5: Complete Delivery
- [ ] Todas as 12 tarefas implementadas e verificadas individualmente.
- [ ] Zero erros de lint, formato ou tipagem estrita no `make pre-commit`.
- [ ] Documentação e rastreabilidade sincronizadas.
