# SPEC-resilient-data-source-sync: Sincronização Resiliente de Fontes de Dados (Native Async HTTP Client, Semáforo de Concorrência, Retry, DLQ e Reprocessamento UI)

## 1. Contexto e Motivação

Durante a sincronização da pasta de daily meetings do Google Drive contendo 14 arquivos `.docx` na Knowledge Base `18d634c4-6c5b-4273-b0b3-cc00433b8be4`, 14 arquivos foram descobertos com sucesso, mas apenas 4 foram anexados e indexados. Os outros 10 arquivos falharam no meio do download.

### Causa Raiz Diagnosticada
1. **Falta de Thread-Safety no Client Google:** A biblioteca oficial `google-api-python-client` (`build('drive', 'v3')`) encapsula `httplib2.Http`, que é explicitamente não thread-safe.
2. **Concorrência Desenfreada no Use Case:** `SyncDataSourceUseCase` executou `asyncio.gather(*[_process_item(item) for item in changes.items])` para todos os 14 itens ao mesmo tempo, despachando 14 corrotinas paralelas em threads (`asyncio.to_thread`).
3. **Colisão de Sockets TLS:** 14 threads simultâneas tentaram ler e escrever no mesmo socket SSL do client compartilhado, corrompendo os frames TLS com a exceção nativa `[SSL] record layer failure (_ssl.c:2580)` em 10 das 14 threads.
4. **Avanço Prematuro de Cursor:** O caso de uso chamou `data_source.complete_sync(new_cursor=changes.next_cursor)` incondicionalmente, avançando o cursor do Google Drive para o token `52`. Como o cursor avançou, qualquer nova sincronização incremental ignora os 10 arquivos perdidos.
5. **Invisibilidade e Discrepância na UI:** No front-end, o Card da fonte de dados exibia apenas status genérico ("Idle"), e no modal de histórico de execuções havia um bug de tipagem que tentava ler `fail.name` em vez de `fail.file_name`, ocultando o nome do arquivo com falha e sem opção para reprocessar os itens da DLQ.

---

## 2. Objetivos e Critérios de Sucesso

### 2.1 Objetivos Centrais
1. **Client HTTP Assíncrono Nativo (`httpx.AsyncClient`):**
   - Substituir a dependência de `google-api-python-client` / `MediaIoBaseDownload` no download de arquivos por um cliente assíncrono direto baseado em `httpx`, com pool de conexões HTTP/2 e TLS isolado.
   - Renovação de tokens OAuth2 coroutine-safe via `asyncio.Lock()` e `asyncio.to_thread(credentials.refresh, ...)`.
2. **Controle de Concorrência Bounded (`asyncio.Semaphore(3)`):** Limitar o paralelismo de downloads simultâneos (máximo 3 por padrão) no caso de uso, evitando gargalo de rede e saturação de I/O.
3. **Retry Automático com Backoff Exponencial:** Capturar falhas transitórias de transporte (quedas de socket, 429 rate limit, 503) e realizar até 3 tentativas automáticas antes de mover o item para a DLQ.
4. **Prevenção de Desperdício de Tokens (Idempotency Gate Pré-Download):**
   - Antes de iniciar o download de qualquer arquivo, checar se ele já existe na KB indexado com o mesmo `external_id` e `version_hash`. Se inalterado, pular download e attach (`SKIPPED_UNCHANGED`), eliminando re-processamento duplicado e gasto de LLM.
5. **Dead Letter Queue (DLQ) & Cursor Seguro:**
   - Enriquecer `DataSourceRun.record_document_failed` para armazenar `doc_id`, `file_name`, `error`, `external_id`, `mime_type`, `version_hash` e `size_bytes`.
   - Adicionar `pending_cursor` no `DataSourceRun`. Se houver qualquer falha no lote, o cursor da fonte de dados **não avança** e o token de continuação é armazenado no run.
   - Eliminar o bug de sobrescrita de falhas em memória (`run = latest_run`) salvando o run com segurança.
6. **Reprocessamento Manual Inteligente via UI (Dual-Route Retry):**
   - Criar `RetryFailedDataSourceItemsUseCase` e endpoint `POST /kbs/{kb_id}/data-sources/{data_source_id}/runs/{run_id}/retry`.
   - Roteamento inteligente:
     - Falha de Download (`doc_id is None`): Re-baixa do Google Drive usando `external_id` e `mime_type`, depois executa attach.
     - Falha de Ingestão (`doc_id is not None`): Invoca `ReprocessDocumentUseCase(doc_id)`, reutilizando o binário no Object Storage sem re-download.
   - Se o retry recuperar 100% dos itens do run, o `DataSource.cursor` é promovido com o `pending_cursor`.
   - Trava de concorrência com validação de status `SYNCING` (409 Conflict se já em execução).
7. **Visibilidade e Ação na UI:**
   - Correção do bug de exibição (`fail.file_name || fail.name`) no modal.
   - Botão de ação rápida "Reprocessar Falhas" no `DataSourceRunsModal` e alerta visual de falhas parciais no `DataSourceCard`.

---

## 3. Tech Stack

- **Linguagem:** Python 3.12+ com Mypy em modo estrito (`strict = true`).
- **HTTP Client:** `httpx` (assíncrono nativo, connection pooling, streaming I/O).
- **Autenticação:** `google-auth` (`service_account.Credentials`).
- **Backend Framework:** FastAPI, asyncio.
- **Frontend:** React 19, TypeScript, Tailwind CSS, Lucide Icons, TanStack Query (React Query).
- **Banco de Dados:** PostgreSQL 16 (CQRS Read/Write Models).

---

## 4. Commands

- **Build & Gates de Verificação Completo:**
  ```bash
  make pre-commit
  ```
- **Execução dos Testes Unitários e Integração:**
  ```bash
  poetry run pytest tests/modules/knowledge/infrastructure/test_google_drive_http_client.py tests/modules/knowledge/application/test_sync_data_source_resilience.py tests/modules/knowledge/application/test_retry_failed_data_source_items.py -v
  ```
- **Lint e Formatação:**
  ```bash
  poetry run ruff check .
  poetry run ruff format --check .
  ```
- **Checagem de Tipos Estrita (Zero Any implícito):**
  ```bash
  poetry run mypy src/
  ```

---

## 5. Project Structure

```
src/
├── api_gateway/
│   ├── controllers/
│   │   └── data_source_controller.py                     # Novo endpoint POST /runs/{run_id}/retry
│   └── dtos/
│       ├── retry_failed_data_source_items_response_dto.py # DTO de resposta do retry
│       └── data_source_run_response_dto.py               # Enriquecimento com failure_summary e pending_cursor
├── modules/
│   └── knowledge/
│       ├── application/
│       │   └── use_cases/
│       │       ├── sync_data_source/
│       │       │   └── sync_data_source_use_case.py       # Semáforo, idempotency gate, retry, safe cursor
│       │       └── retry_failed_data_source_items/        # Caso de uso de reprocessamento dual
│       │           ├── __init__.py
│       │           ├── retry_failed_data_source_items_request.py
│       │           ├── retry_failed_data_source_items_response.py
│       │           └── retry_failed_data_source_items_use_case.py
│       ├── domain/
│       │   └── entities/
│       │       └── data_source_run.py                     # pending_cursor e record_document_failed enriquecido
│       └── infrastructure/
│           └── adapters/
│               └── google_drive/
│                   ├── google_drive_http_client.py        # Client HTTP httpx com lock no token refresh
│                   └── google_drive_folder_connector.py   # Refatorado para usar GoogleDriveHttpClient
frontend/
└── src/
    ├── api/
    │   └── dataSources.ts                                 # Função retryFailedDataSourceItems
    ├── hooks/
    │   └── useDataSources.ts                              # Hook useRetryFailedDataSourceItems
    └── components/
        └── data-sources/
            ├── DataSourceCard.tsx                         # Alerta visual de falha na última execução
            └── DataSourceRunsModal.tsx                    # Correção file_name + Botão Reprocessar Falhas
tests/
└── modules/
    └── knowledge/
        ├── application/
        │   ├── test_sync_data_source_resilience.py        # Testes de concorrência, idempotency gate e cursor
        │   └── test_retry_failed_data_source_items.py     # Testes de reprocessamento dual (download vs doc_id)
        └── infrastructure/
            └── test_google_drive_http_client.py           # Teste unitário do client httpx e token lock
```

---

## 6. Code Style e Padrões Arquiteturais

### 6.1 `GoogleDriveHttpClient` com Lock Coroutine-Safe no Token Refresh

```python
import asyncio
from typing import Any
import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.service_account import Credentials


class GoogleDriveHttpClient:
    def __init__(self, credentials: Credentials) -> None:
        self._credentials = credentials
        self._client: httpx.AsyncClient | None = None
        self._refresh_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=15.0, read=120.0, write=30.0, pool=60.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    async def _get_access_token(self) -> str:
        async with self._refresh_lock:
            if not self._credentials.valid:
                await asyncio.to_thread(self._credentials.refresh, GoogleAuthRequest())
            token: str = str(self._credentials.token)
            return token

    async def download_file(self, file_id: str) -> bytes:
        client = await self._get_client()
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = (
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
        )
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.content

    async def export_file(self, file_id: str, mime_type: str) -> bytes:
        client = await self._get_client()
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
        response = await client.get(
            url, headers=headers, params={"mimeType": mime_type, "supportsAllDrives": "true"}
        )
        response.raise_for_status()
        return response.content

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
```

### 6.2 Idempotency Gate Pré-Download no `SyncDataSourceUseCase`

```python
# Mapeia docs existentes na KB indexados por external_id
existing_indexed_by_external_id: dict[str, str] = {
    doc.source_metadata.get("external_id"): doc.source_metadata.get("version_hash", "")
    for doc in existing_docs
    if doc.source_metadata and "external_id" in doc.source_metadata
}

if (
    item.external_id in existing_indexed_by_external_id
    and existing_indexed_by_external_id[item.external_id] == item.version_hash
):
    self._log_info(f"Item '{item.name}' já indexado e inalterado. Pulando download.")
    # Registra como sucesso no run sem baixar nem pagar tokens de LLM
    run.record_document_indexed()
    return
```

---

## 7. Testing Strategy

1. **Unit Tests (`test_google_drive_http_client.py`):**
   - Mockar respostas HTTP com `unittest.mock` / `respx`.
   - Testar download binário, exportação Docs/Sheets, concorrência no token refresh (`asyncio.gather`) e tratamento de erros 403/404.
2. **Resilience & Idempotency Tests (`test_sync_data_source_resilience.py`):**
   - Testar que itens com mesmo `external_id` e `version_hash` não são baixados.
   - Testar semáforo limitando downloads a 3 simultâneos.
   - Validar que o `cursor` do DataSource NÃO avança quando há falhas parciais e que `pending_cursor` é gravado no run.
   - Validar que o status do run torna-se `PARTIALLY_FAILED` com `failure_summary` contendo `external_id` e `mime_type`.
3. **Reprocess Use Case Tests (`test_retry_failed_data_source_items.py`):**
   - Testar roteamento dual: itens com `doc_id is None` são baixados novamente; itens com `doc_id is not None` chamam `ReprocessDocumentUseCase`.
   - Testar que, ao zerar as falhas, o `DataSource.cursor` é promovido com o `run.pending_cursor`.
   - Testar rejeição com erro de conflito quando `data_source.status == SYNCING`.

---

## 8. Boundaries

### Always
- Executar `make pre-commit` antes de qualquer commit (Mypy estrito, Ruff, 100% dos testes passando).
- Manter estritamente a regra inegociável de **Single Class per File** do `AGENTS.md`.
- Garantir `async/await` nativo em todas as operações de rede e conector.
- Proteger chamadas externas ao Google com limites de concorrência e timeout explícito.

### Ask First
- Alterações em schemas de banco de dados ou tabelas existentes.
- Adição de novas dependências pesadas externas no `pyproject.toml`.

### Never
- Usar clientes HTTP ou sockets compartilhados entre threads sem thread-safety.
- Avançar cursores de sincronização se houver itens que falharam no download ou anexação.
- Engolir exceções em loops concorrentes sem registrar o erro detalhado no `failure_summary`.
- Re-baixar arquivos que já estejam indexados com versão idêntica na KB.

---

## 9. Success Criteria

1. [ ] **Zero Erros de SSL:** Não há ocorrência de `[SSL] record layer failure` mesmo ao sincronizar pastas com dezenas de arquivos concorrentes.
2. [ ] **Idempotência Garantida:** Arquivos já indexados não são re-baixados nem re-enviados para LLM.
3. [ ] **DLQ Completa & Roteamento Dual:** `failure_summary` contém metadados completos (`external_id`, `mime_type`), permitindo reprocessamento preciso.
4. [ ] **Promoção Segura de Cursor:** O cursor da fonte avança imediatamente se tudo passar, ou via `pending_cursor` após a recuperação de todas as falhas.
5. [ ] **UI Transparente e Acionável:**
   - Card alerta falha na última execução.
   - Modal exibe nomes legíveis dos arquivos com erro.
   - Botão "Reprocessar Falhas" no modal reprocessa os itens da DLQ e atualiza a interface.
6. [ ] **Recuperação dos 10 Arquivos:** Ao resetar o cursor e sincronizar, todos os 14 arquivos `.docx` da pasta de daily meetings são baixados e indexados com sucesso no FalkorDB.
