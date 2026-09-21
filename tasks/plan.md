# Implementation Plan: Google Drive Folder Data Source & Blue/Green Ingestion (Marco 1.25)

## 1. Overview
Implementar o subsistema de **`DataSource`** no módulo `knowledge` do **Agentic Substrate**, permitindo que uma Knowledge Base seja vinculada a uma ou mais pastas do Google Drive através de Service Account GCP. O conector opera como um **Upstream Producer (Extract & Load)** com streaming em memória $O(1)$ via semáforo assíncrono, desacoplamento via resposta imediata `202 Accepted`, rastreabilidade ponta a ponta através da entidade `DataSourceRun`, e reprocessamento sem downtime através da estratégia **Blue/Green Document Atomic Swap** coordenada por eventos.

---

## 2. Architecture Decisions
- **Clean Architecture Pura:** A entidade `DataSource` e o agregado no domínio são 100% agnósticos a fornecedores externos. A API do Google Drive reside exclusivamente em `infrastructure/adapters/google_drive/google_drive_folder_connector.py`.
- **Adaptador Granular Especializado:** Em vez de um "God Adapter", o `GoogleDriveFolderConnector` é focado unicamente na lógica de pastas (`folder_id`), varredura hierárquica e conversão de formatos proprietários do Google.
- **Upstream Producer sem Bloqueio de Sagas:** O worker do conector apenas extrai e persiste os arquivos brutos via `AttachAndStoreDocumentUseCase`, liberando a memória imediatamente e finalizando sua execução física. As Sagas de GraphRAG rodam assincronamente no seu próprio ritmo.
- **Rastreabilidade por Correlation ID (`DataSourceRun`):** Cada sincronização gera um `sync_run_id` carimbado nos documentos. Um projector orientado a eventos (`DataSourceRunProjector`) escuta `DocumentIndexedEvent` e `DocumentIngestionFailedEvent` para atualizar o progresso e o status final da execução.
- **Blue/Green Document Atomic Swap:** Ao detectar que um arquivo no Drive teve seu `version_hash` alterado, a nova versão é processada isoladamente enquanto a versão anterior continua ativa. Um handler reativo (`BlueGreenDocumentSwapHandler`) escuta `DocumentIndexedEvent` e purga atomicamente o subgrafo antigo via `DeleteDocumentUseCase`.
- **Single Class per File & Mypy Strict:** Nenhuma classe, DTO, protocolo ou entidade agrupada em mono-arquivos. Tipagem estrita com `Result[T, DomainError]` em todos os use cases.

---

## 3. Dependency Graph

```
[Phase 1] Value Objects, Domain Entities, Events e Protocols
    │
    ├── [Phase 2] Migração PostgreSQL e Repositórios (DataSource e DataSourceRun)
    │       │
    │       └── [Phase 3] Adaptadores de Infraestrutura (Mock, Registry, GoogleDriveFolderConnector)
    │               │
    │               └── [Phase 4] Application Layer: Use Cases, Sync Worker e Handlers (Swap & Run Projector)
    │                       │
    │                       └── [Phase 5] API Gateway: DTOs, Controller e IoC Container Wiring
    │                               │
    │                               └── [Phase 6] Testes de Integração E2E e Gate make pre-commit
```

---

## 4. Phase Breakdown

### Phase 1: Domain Primitives & Value Objects (Tasks 1 & 2)
- Value Objects: `DataSourceType`, `DataSourceStatus`, `DataSourceRunStatus`, `GoogleDriveFolderConfig`, `DiscoveredDocumentItem`, `DataSourceChangesBatch`.
- Entidades de Domínio: `DataSource`, `DataSourceRun`.
- Eventos de Domínio: `DataSourceCreatedEvent`, `DataSourceSyncStartedEvent`, `DataSourceSyncCompletedEvent`, `DataSourceSyncFailedEvent`, `DataSourceRunCompletedEvent`.
- Interfaces/Protocols: `IDataSourceConnector`, `IDataSourceConnectorRegistry`, `IDataSourceRepository`, `IDataSourceRunRepository`.
- Testes unitários do domínio em `tests/unit/test_data_source_domain.py`.

### Phase 2: Relational Persistence & Repositories (Tasks 3 & 4)
- Migração Alembic `0007_create_knowledge_data_sources.py` criando as tabelas `knowledge_data_sources` e `knowledge_data_source_runs`.
- Implementações In-Memory e PostgreSQL para `IDataSourceRepository` e `IDataSourceRunRepository`.
- Testes unitários/integração de persistência em `tests/unit/test_data_source_repositories.py`.

### Phase 3: Infrastructure Adapters & Connectors (Tasks 5 & 6)
- `InMemoryDataSourceConnector` para testes determinísticos.
- `DataSourceConnectorRegistry` mapeando `DataSourceType.GOOGLE_DRIVE_FOLDER` para a implementação concreta.
- `GoogleDriveFolderConnector` utilizando a API v3 do Google Drive (`files.list`, `changes.list`, `files.export`, `files.get`).
- Testes unitários de adaptador em `tests/unit/test_google_drive_folder_connector.py`.

### Phase 4: Application Layer — Use Cases & Event Handlers (Tasks 7, 8 & 9)
- Use Cases de Gestão: `CreateDataSourceUseCase`, `ListDataSourcesUseCase`, `ListDataSourceRunsUseCase`, `DeleteDataSourceUseCase`.
- Sincronização Assíncrona: `SyncDataSourceUseCase` com semáforo de concorrência (`asyncio.Semaphore(max_concurrency=2)`), criação de `DataSourceRun` e handoff para `AttachAndStoreDocumentUseCase`.
- Handlers Reativos:
  - `BlueGreenDocumentSwapHandler`: escuta `DocumentIndexedEvent` e purga o doc anterior quando `replaces_doc_id` estiver presente.
  - `DataSourceRunProjector`: escuta eventos de conclusão e falha para consolidar as métricas de cada execução.
- Testes unitários de use cases e handlers.

### Phase 5: API Gateway, DTOs & Container Wiring (Tasks 10 & 11)
- DTOs em `src/api_gateway/dtos/` para request/response de criação, listagem, status e runs.
- Controller em `src/api_gateway/controllers/data_source_controller.py` com rotas `/api/v1/knowledge-bases/{kb_id}/data-sources`.
- Injeção de dependências no `Container` (`src/api_gateway/container.py`) e inclusão de rotas no `main.py`.

### Phase 6: E2E Integration Tests & Quality Gates (Task 12)
- Testes de ponta a ponta na API Gateway (`tests/integration/test_data_source_api_gateway.py`).
- Teste E2E do fluxo de sincronização e swap atômico no FalkorDB (`tests/integration/test_e2e_data_source_sync_and_swap.py`).
- Execução dos quality gates oficiais: `make pre-commit` (Ruff linter/formatter, Mypy strict mode, Pytest com 100% de aprovação).

---

## 5. Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Quotas e Rate Limit da Google Drive API v3 (1000 req/100s) | Médio | Extração em streaming com semáforo (`max_concurrency=2`) e caching local de metadados por `version_hash`. |
| Arquivo Google Docs nativo corrompido ou vazio na exportação | Médio | Tratamento individual de exceções por arquivo: registra falha no `failure_summary` da run e prossegue para os próximos arquivos. |
| Remoção acidental de subgrafo compartilhado no swap do FalkorDB | Alto | O `DeleteDocumentUseCase` já implementado usa exclusão estrita de nós do documento preservando entidades ontológicas conectadas. |
| Ingestões concorrentes na mesma pasta do Drive | Médio | Lock no nível da entidade `DataSource` (`status == SYNCING` rejeita novos disparos como No-Op). |
