# SPEC-google-drive-folder-data-source: Google Drive Folder Data Source, Upstream Producer & Blue/Green Document Ingestion

## 1. Contexto e Motivação
O **Agentic Substrate** provê um motor assíncrono de GraphRAG corporativo de alto desempenho, transformando documentos brutos em grafos ontológicos particionados por Knowledge Base (`KnowledgeBaseAggregate`) no FalkorDB e PostgreSQL.

Originalmente, os documentos entram no substrato via upload HTTP multipart direto através de [`AttachAndStoreDocumentUseCase`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/application/use_cases/attach_and_store_document/attach_and_store_document_use_case.py). No entanto, para viabilizar a criação de bases de conhecimento corporativas autônomas e sem fricção humana, o sistema necessita conectar-se a fontes externas de dados corporativos (ex: Google Drive, Slack, pastas de rede).

Esta especificação define o subsistema agnóstico de **`DataSource`** no domínio e implementa o conector especializado granular **`GoogleDriveFolderConnector`** na infraestrutura, operando como um **Upstream Producer (Extract & Load)** que alimenta o pipeline GraphRAG existente e aplica a estratégia **Blue/Green Document Atomic Swap** para reprocessamento de novas versões sem downtime e com zero risco de alucinação por contradição factual.

---

## 2. Arquitetura em Clean Architecture: Separação Domínio vs. Infraestrutura

O conector adota o princípio de **Ports & Adapters (Hexagonal)** para impedir o vazamento de APIs e SDKs de terceiros (Google) para as regras de negócio centrais:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ DOMAIN LAYER (Puro, Agnóstico a Vendor)                                                │
│                                                                                        │
│  Entidade: DataSource                                                                  │
│  - id: UUID                                                                            │
│  - kb_id: UUID                                                                         │
│  - name: str                                                                           │
│  - data_source_type: DataSourceType (ex: GOOGLE_DRIVE_FOLDER)                          │
│  - status: DataSourceStatus (IDLE, SYNCING, FAILED)                                    │
│  - cursor: str | None (watermark/pageToken agnóstico de delta)                         │
│  - sync_interval_minutes: int                                                          │
│  - last_synced_at: datetime | None                                                     │
│  - config: dict[str, Any] (folder_id, recursive, baseline_days, etc.)                 │
│                                                                                        │
│  Port / Interface: IDataSourceConnector                                                │
│  - fetch_changes(config, cursor) -> DataSourceChangesBatch                             │
│  - download_document(external_id, mime_type) -> DiscoveredDocumentPayload              │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ (Implementa o Port)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE LAYER (Especialistas de Terceiros)                                      │
│                                                                                        │
│  Adapter: GoogleDriveFolderConnector(IDataSourceConnector)                             │
│  - Autenticação por Service Account GCP (sem OAuth 3-legged)                          │
│  - Varredura de diretório (parents in folder_id) e detecção de delta com changes.list   │
│  - Conversão de Google Docs/Sheets nativos para Markdown/CSV/Plaintext                 │
│  - Download streaming de binários (PDF, Áudio, Imagens)                                │
│                                                                                        │
│  Registry: DataSourceConnectorRegistry(IDataSourceConnectorRegistry)                   │
│  - Mapeamento determinístico: DataSourceType.GOOGLE_DRIVE_FOLDER ➔ GoogleDriveFolder.. │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Ciclo de Vida e Fluxo de Execução (Upstream Producer + Blue/Green Swap)

O conector atua estritamente na fase de **Extract** e **Load Bruto**, entregando o artefato para a Saga existente (**Transform & Index**):

```mermaid
sequenceDiagram
    autonumber
    actor Trigger as Cron Worker / Manual API
    participant SyncUC as SyncDataSourceUseCase
    participant Registry as DataSourceConnectorRegistry
    participant Adapter as GoogleDriveFolderConnector
    participant GDriveAPI as Google Drive API v3
    participant AttachUC as AttachAndStoreDocumentUseCase
    participant Saga as DocumentIngestionSagaCoordinator
    participant Falkor as FalkorDB GraphStore
    participant SwapHandler as BlueGreenDocumentSwapHandler
    participant DeleteUC as DeleteDocumentUseCase

    Trigger->>SyncUC: execute(kb_id, data_source_id)
    SyncUC-->>Trigger: 202 Accepted (Execução despachada em Background Worker)
    SyncUC->>Registry: get_connector(data_source.type)
    Registry-->>SyncUC: GoogleDriveFolderConnector instance
    
    Note over SyncUC,GDriveAPI: FASE 1: Descoberta Leve de Metadados (Zero Download de Binários)
    SyncUC->>Adapter: fetch_changes(config, cursor)
    Adapter->>GDriveAPI: files.list / changes.list(pageToken)
    GDriveAPI-->>Adapter: raw items (metadata, mtime, hash)
    Adapter-->>SyncUC: DataSourceChangesBatch (items, next_cursor)

    Note over SyncUC,AttachUC: FASE 2: Bounded Extraction Loop (asyncio.Semaphore, max_concurrency=2)
    loop Para cada item modificado ou novo (streaming O(1) de memória)
        SyncUC->>Adapter: download_document(external_id, mime)
        Adapter->>GDriveAPI: files.export (Docs) ou files.get(alt='media')
        GDriveAPI-->>Adapter: bytes_content, resolved_mime, version_hash
        
        alt Arquivo já existia na KB com version_hash diferente (Nova Versão)
            Note over SyncUC: Identifica old_doc_id associado ao external_id<br/>Define replaces_doc_id = old_doc_id
        end

        SyncUC->>AttachUC: execute(kb_id, file_name, content, replaces_doc_id, metadata)
        AttachUC-->>Saga: DocumentStoredEvent(new_doc_id, replaces_doc_id)
        Note over SyncUC: Libera bytes_content da memória imediatamente
        
        Note over Saga: Ingestão paralela isolada (new_doc_id):<br/>VLM/OCR ➔ Chunker ➔ Embeddings ➔ FalkorDB
        Saga->>Falkor: Indexa subgrafo do new_doc_id
        Saga-->>SwapHandler: DocumentIndexedEvent(new_doc_id, replaces_doc_id)

        opt replaces_doc_id is not None (Blue/Green Swap Atômico)
            SwapHandler->>DeleteUC: execute(kb_id, old_doc_id)
            DeleteUC->>Falkor: delete_document_subgraph(kb_id, old_doc_id)
            Note over Falkor: Subgrafo obsoleto removido atomicamente sem downtime
        end
    end

    SyncUC->>SyncUC: Atualiza cursor = next_cursor, status = IDLE, last_synced_at = now

### 3.1 Mecânica do Background Worker & Controle de Vazão
1. **Desacoplamento Assíncrono Total (Fast 202 Accepted):**
   - O endpoint HTTP de sincronização manual (`POST /sync`) e o cron periódico nunca bloqueiam a requisição esperando downloads. Eles validam o estado, alteram o status para `SYNCING` e despacham a execução para uma tarefa assíncrona em background, retornando `202 Accepted` em `< 50ms`.
2. **Consumo de Memória Constante ($O(1)$):**
   - Se uma pasta contiver dezenas ou centenas de arquivos, o worker **não faz buffer de múltiplos binários simultâneos na RAM**.
   - A extração utiliza um semáforo de controle de vazão (`asyncio.Semaphore(max_concurrency=2)`): cada arquivo é baixado, imediatamente gravado em disco no `IObjectStorage` através do `AttachAndStoreDocumentUseCase` e liberado da memória antes do próximo download.
3. **Isolamento de Falhas por Arquivo (Fault Tolerance):**
   - Se um arquivo específico sofrer timeout ou erro de decodificação na API do Google, o erro é registrado no log e nos metadados do conector, mas o loop de sincronização **continua para os demais arquivos**.
4. **Idempotência e Lock de Sincronização:**
   - Caso um novo ciclo de sync seja disparado enquanto uma sincronização já estiver em andamento (`status == SYNCING`), a nova solicitação é descartada de forma segura (*No-Op*).

### 3.2 Rastreabilidade End-to-End: `DataSourceRun` & Correlation ID
Para que o sistema mantenha vínculo explícito entre a execução do worker, os arquivos descobertos e o sucesso ou fracasso de cada documento no pipeline GraphRAG:

1. **Abertura da Execução (`DataSourceRun`):**
   - No início da sincronização, é instanciada uma entidade `DataSourceRun(id=UUID, data_source_id=UUID, kb_id=UUID, status=EXTRACTING)`.
2. **Carimbo de Procedência no Documento:**
   - Cada documento salvo recebe em seus metadados de domínio:
     ```python
     source_type = "data_source"
     source_metadata = {
         "data_source_id": str(data_source.id),
         "sync_run_id": str(run.id),
         "external_file_id": item.external_id,
         "version_hash": item.version_hash,
     }
     ```
3. **Transição para `INGESTING`:**
   - Ao finalizar os downloads e entregar todos os arquivos para o `AttachAndStoreDocumentUseCase`, o worker atualiza o `DataSourceRun` para `status = INGESTING`, registrando `total_files_discovered = K`. O worker encerra sua execução física com sucesso.
4. **Atualização Reativa Orientada a Eventos (`DataSourceRunProjector`):**
   - O handler `DataSourceRunProjector` escuta os eventos da Saga:
     - `DocumentIndexedEvent` ➔ incrementa `indexed_files_count`.
     - `DocumentIngestionFailedEvent` ➔ incrementa `failed_files_count` e anexa o arquivo/erro no `failure_summary`.
   - Quando `indexed_files_count + failed_files_count == total_files_discovered`:
     - Se `failed_files_count == 0`: marca `status = COMPLETED`.
     - Se `failed_files_count > 0` e `indexed_files_count > 0`: marca `status = PARTIALLY_FAILED`.
     - Se `indexed_files_count == 0`: marca `status = FAILED`.
     - Registra `completed_at = now()` e emite `DataSourceRunCompletedEvent`.

---

## 4. Matriz de Formatos e Conversão do Google Drive

| MimeType Original no Google Drive | Estratégia de Extração | Formato Entregue ao Pipeline |
|---|---|---|
| `application/vnd.google-apps.document` | `files.export(mimeType='text/plain')` ou Markdown | `.txt` / `.md` (Texto estruturado) |
| `application/vnd.google-apps.spreadsheet` | `files.export(mimeType='text/csv')` | `.csv` (Tabela delimitada) |
| `application/pdf` | `files.get(alt='media')` | `.pdf` (Encaminhado para VLM/OCR) |
| `audio/mpeg`, `audio/wav`, `audio/x-m4a` | `files.get(alt='media')` | Áudio bruto (Encaminhado para Whisper) |
| `image/png`, `image/jpeg`, `image/webp` | `files.get(alt='media')` | Imagem bruta (Encaminhada para VLM) |
| `text/plain`, `text/markdown` | `files.get(alt='media')` | `.txt` / `.md` (Fast-path direto) |

---

## 5. Project Structure (Single Class per File — Regra Inegociável)

Em conformidade rigorosa com o [AGENTS.md](file:///Users/insider/personal/agentic-substrate/AGENTS.md), cada classe, protocolo, DTO e evento possui seu próprio arquivo:

```
src/modules/knowledge/
├── domain/
│   ├── entities/
│   │   ├── data_source.py
│   │   ├── data_source_run.py                    # Entidade que rastreia o ciclo de vida de uma execução de sync
│   │   └── __init__.py
│   ├── value_objects/
│   │   ├── data_source_type.py                   # Enum: GOOGLE_DRIVE_FOLDER, LOCAL_DIRECTORY
│   │   ├── data_source_status.py                 # Enum: IDLE, SYNCING, FAILED, DISABLED
│   │   ├── data_source_run_status.py             # Enum: EXTRACTING, INGESTING, COMPLETED, PARTIALLY_FAILED, FAILED
│   │   ├── google_drive_folder_config.py         # VO: folder_id, recursive, baseline_days, mime_types
│   │   ├── discovered_document_item.py           # VO: external_id, name, mime_type, version_hash, mtime
│   │   ├── data_source_changes_batch.py          # VO: items, next_cursor, deleted_external_ids
│   │   └── __init__.py
│   ├── events/
│   │   ├── data_source_created_event.py
│   │   ├── data_source_sync_started_event.py
│   │   ├── data_source_sync_completed_event.py
│   │   ├── data_source_sync_failed_event.py
│   │   ├── data_source_run_completed_event.py
│   │   └── __init__.py
│   └── interfaces/
│       ├── i_data_source_connector.py            # Protocol: fetch_changes, download_document
│       ├── i_data_source_connector_registry.py   # Protocol: get_connector(data_source_type)
│       ├── i_data_source_repository.py           # Protocol: CRUD e persistência do DataSource
│       ├── i_data_source_run_repository.py       # Protocol: Persistência e consulta de DataSourceRun
│       └── __init__.py
│
├── application/
│   ├── use_cases/
│   │   ├── create_data_source/
│   │   │   ├── create_data_source_request.py
│   │   │   ├── create_data_source_response.py
│   │   │   ├── create_data_source_use_case.py
│   │   │   └── __init__.py
│   │   ├── sync_data_source/
│   │   │   ├── sync_data_source_request.py
│   │   │   ├── sync_data_source_response.py
│   │   │   ├── sync_data_source_use_case.py
│   │   │   └── __init__.py
│   │   ├── list_data_sources/
│   │   │   ├── list_data_sources_request.py
│   │   │   ├── list_data_sources_response.py
│   │   │   ├── list_data_sources_use_case.py
│   │   │   └── __init__.py
│   │   ├── list_data_source_runs/
│   │   │   ├── list_data_source_runs_request.py
│   │   │   ├── list_data_source_runs_response.py
│   │   │   ├── list_data_source_runs_use_case.py
│   │   │   └── __init__.py
│   │   ├── delete_data_source/
│   │   │   ├── delete_data_source_request.py
│   │   │   ├── delete_data_source_response.py
│   │   │   ├── delete_data_source_use_case.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── handlers/
│   │   ├── blue_green_document_swap_handler.py    # Escuta DocumentIndexedEvent e executa swap
│   │   ├── data_source_run_projector.py          # Atualiza DataSourceRun conforme documentos indexam ou falham
│   │   └── __init__.py
│   └── __init__.py
│
└── infrastructure/
    ├── adapters/
    │   ├── google_drive/
    │   │   ├── google_drive_folder_connector.py  # Implementa IDataSourceConnector com Google API v3
    │   │   └── __init__.py
    │   ├── in_memory_data_source_connector.py    # Mock de alta fidelidade para testes
    │   ├── data_source_connector_registry.py     # Implementa IDataSourceConnectorRegistry
    │   └── __init__.py
    └── repositories/
        ├── postgres_data_source_repository.py    # Persistência na tabela knowledge_data_sources
        ├── postgres_data_source_run_repository.py# Persistência na tabela knowledge_data_source_runs
        ├── in_memory_data_source_repository.py   # Repositório in-memory para testes unitários
        ├── in_memory_data_source_run_repository.py# Repositório in-memory de runs
        └── __init__.py

src/api_gateway/
├── controllers/
│   ├── data_source_controller.py                 # Rotas /api/v1/knowledge-bases/{kb_id}/data-sources
│   └── __init__.py
└── dtos/
    ├── create_data_source_dto.py
    ├── data_source_response_dto.py
    ├── data_source_run_response_dto.py
    ├── sync_data_source_response_dto.py
    └── __init__.py
```

---

## 6. Persistência Relacional (PostgreSQL)

Novas tabelas gerenciadas via migração Alembic (`0007_create_knowledge_data_sources.py`):

```sql
CREATE TABLE knowledge_data_sources (
    id UUID PRIMARY KEY,
    kb_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    data_source_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'IDLE',
    cursor TEXT NULL,
    sync_interval_minutes INT NOT NULL DEFAULT 15,
    last_synced_at TIMESTAMP WITH TIME ZONE NULL,
    error_message TEXT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE knowledge_data_source_runs (
    id UUID PRIMARY KEY,
    data_source_id UUID NOT NULL REFERENCES knowledge_data_sources(id) ON DELETE CASCADE,
    kb_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'EXTRACTING',
    total_files_discovered INT NOT NULL DEFAULT 0,
    indexed_files_count INT NOT NULL DEFAULT 0,
    failed_files_count INT NOT NULL DEFAULT 0,
    failure_summary JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE NULL
);

CREATE INDEX idx_data_sources_kb_id ON knowledge_data_sources(kb_id);
CREATE INDEX idx_data_sources_status ON knowledge_data_sources(status);
CREATE INDEX idx_data_source_runs_ds_id ON knowledge_data_source_runs(data_source_id);
CREATE INDEX idx_data_source_runs_status ON knowledge_data_source_runs(status);
```

---

## 7. Testing Strategy

* **Unit Tests (`tests/unit/`):**
  - `test_data_source_entity.py`: Validação de invariantes, transições de status (IDLE ➔ SYNCING ➔ IDLE/FAILED) e avanço do cursor.
  - `test_google_drive_folder_config.py`: Validação de `folder_id` obrigatório e sanitização de `baseline_days`.
  - `test_create_data_source_use_case.py`: Criação de data source com validação de existência da KB.
  - `test_sync_data_source_use_case.py`: Simulação de sincronização com `InMemoryDataSourceConnector`, verificando que novos arquivos acionam `AttachAndStoreDocumentUseCase`.
  - `test_blue_green_document_swap_handler.py`: Garantir que `DocumentIndexedEvent` sem `replaces_doc_id` não executa deleções, e com `replaces_doc_id` invoca `DeleteDocumentUseCase`.
* **Integration Tests (`tests/integration/`):**
  - `test_postgres_data_source_repository.py`: CRUD real no banco PostgreSQL.
  - `test_data_source_api_gateway.py`: Teste dos endpoints FastAPI (`POST`, `GET`, `DELETE`, `POST /sync`).
  - `test_e2e_google_drive_folder_sync_and_swap.py`: Teste ponta a ponta simulando a descoberta de nova versão de arquivo e validação de que o subgrafo anterior é expurgado do FalkorDB.

---

## 8. Boundaries

### Always do:
- 1 Classe / 1 Interface / 1 DTO = 1 Arquivo exclusivo.
- Todas as assinaturas devem ter tipagem Mypy estrita (`strict = true`, sem `Any` implícito).
- Usar o padrão `Result[T, DomainError]` com checagens discriminadas (`if isinstance(res, Err): ... return res.value`).
- Executar todas as operações de I/O de rede e banco de forma assíncrona (`async/await`).
- Proteger contra falhas de rede no download de arquivos do Drive, marcando o conector com `status = FAILED` e salvando a mensagem amigável de erro.

### Ask first:
- Adicionar dependências pesadas de SDK além das bibliotecas oficiais do Google (`google-api-python-client`, `google-auth`).
- Alterar tabelas existentes do banco de dados relacional.

### Never do:
- Incluir segredos ou chaves JSON de Service Account no repositório Git ou em logs.
- Bloquear o event loop chamando chamadas síncronas de SDK sem `asyncio.to_thread`.
- Excluir o documento antigo antes de a nova versão atingir o status `INDEXED` com sucesso no FalkorDB.

---

## 9. Success Criteria (Testáveis e Objetivos)
1. **Configuração Granular:** Capacidade de criar um `DataSource` do tipo `GOOGLE_DRIVE_FOLDER` apontando para um `folder_id` e janela de baseline em dias.
2. **Extração & Conversão:** Download com sucesso de arquivos binários e exportação de Google Docs nativos para Markdown.
3. **Idempotência de Delta:** Executar duas sincronizações consecutivas sem alterações no Drive e garantir **0 downloads ou reprocessamentos** na segunda execução.
4. **Blue/Green Swap Perfeito:** Ao modificar o conteúdo de um arquivo no Drive:
   - A nova versão é indexada completamente.
   - O subgrafo e chunks da versão obsoleta são excluídos do FalkorDB e storage.
   - O grafo resultante não contém nós duplicados da mesma entidade ou texto conflitante.
5. **Quality Gates:** 100% de aprovação no comando oficial `make pre-commit` (Mypy estrito, Ruff linter e formatador).

---

## 10. Modelo de Segurança, Implantação e Gestão de Chaves de Service Account

### 1. Gestão Central de Credenciais no Backend (Zero Chaves no Browser)
- **Não há upload de chaves privadas no frontend**: O formulário do console web nunca aceita arquivos `.json` de Service Account, mitigando riscos de vazamento de credenciais mestras do GCP.
- **Configuração no Host / VM**: A chave privada RSA da Service Account é salva exclusivamente no disco da VM (ex: `deploy/vm/credentials/google-service-account.json`) com permissões `600` ou `700`.
- **Montagem Segura no Docker**: O Docker Compose monta `./credentials:/app/credentials:ro` no serviço `api`.
- **Variável de Ambiente**: Configura-se `GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-service-account.json` no `.env` do backend/VM. Em ambientes GCP gerenciados (Compute Engine, Cloud Run, GKE), o conector herda automaticamente as credenciais da instância via Application Default Credentials (ADC).

### 2. Modelo de Autorização Baseado em Compartilhamento
- O usuário do sistema abre a pasta no Google Drive, clica em **Compartilhar** e convida o e-mail da Service Account (ex: `bot@meu-projeto.iam.gserviceaccount.com`) com perfil de **Leitor (Viewer)**.
- O conector só tem visibilidade sobre arquivos e pastas explicitamente compartilhados com a sua conta.

### 3. Interface de Usuário no Frontend (`/frontend`)
- **Aba "Fontes de Dados / Google Drive"** em cada Knowledge Base (`/knowledge-bases/:kbId`).
- **`CreateDataSourceModal`**: Auto-extrai e sanitiza IDs de pastas a partir de URLs completas do Google Drive, oferecendo seletor de MIME types, intervalo de sync e baseline days.
- **`DataSourceCard`**: Exibe status em tempo real (`IDLE`, `SYNCING`, `FAILED`, `DISABLED`), último sync e ações de trigger e exclusão.
- **`DataSourceRunsModal`**: Permite auditar cada execução de ingestão com contadores de arquivos descobertos, indexados e resumo detalhado de falhas.
