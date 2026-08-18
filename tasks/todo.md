# Task List: Configurable OCR & Optimized Visual Ingestion Pipeline

## Phase 1: Settings, Secrets & OpenRouter Client

### Task 1: Settings & Environment Configuration
- **Description:** Atualizar `AppSettings` em `src/kernel/infrastructure/app_settings.py`, `.env.example` e `.env` com configurações para o OpenRouter (`OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OCR_VISION_MODEL_NAME`, `OCR_MAX_CONCURRENCY`, `OCR_DEFAULT_MARKDOWN_PROMPT`).
- **Acceptance criteria:**
  - [x] `AppSettings` possui campos tipados com `SecretStr` para chave e defaults seguros.
  - [x] `.env.example` e `.env` atualizados e documentados.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/test_app_settings.py` (ou teste de carregamento de settings)
- **Dependencies:** None
- **Files touched:**
  - `src/kernel/infrastructure/app_settings.py`
  - `.env.example`
  - `.env`
- **Estimated scope:** Small (3 files)

---

### Task 2: Implementar `OpenRouterClientFactory`
- **Description:** Criar `OpenRouterClientFactory` em `src/modules/knowledge/infrastructure/adapters/openrouter_client_factory.py` para instanciar o cliente `openai.OpenAI` configurado com base URL do OpenRouter e headers customizados.
- **Acceptance criteria:**
  - [x] Implementa factory respeitando o princípio Single Class per File.
  - [x] Tipagem estrita e retorno do cliente apropriado para o MarkItDown.
- **Verification:**
  - [x] Command: `uv run mypy src/modules/knowledge/infrastructure/adapters/openrouter_client_factory.py --strict`
- **Dependencies:** Task 1
- **Files touched:**
  - `src/modules/knowledge/infrastructure/adapters/openrouter_client_factory.py`
  - `src/modules/knowledge/infrastructure/adapters/__init__.py`
- **Estimated scope:** Small (2 files)

---

## Checkpoint 1: Settings & Client Ready

---

## Phase 2: Domain Interfaces & Aggregate Updates

### Task 3: Atualizar `IDocumentParser` e `DocumentAttachedEvent`
- **Description:** Atualizar o protocolo `IDocumentParser` e o evento de domínio `DocumentAttachedEvent` para aceitarem `enable_ocr: bool = False` e `ocr_instructions: str | None = None`.
- **Acceptance criteria:**
  - [x] `IDocumentParser.parse_to_markdown` recebe `enable_ocr` e `ocr_instructions`.
  - [x] `DocumentAttachedEvent` transporta `enable_ocr` e `ocr_instructions`.
- **Verification:**
  - [x] Command: `uv run mypy src/modules/knowledge/domain/ --strict`
- **Dependencies:** Task 2
- **Files touched:**
  - `src/modules/knowledge/domain/interfaces/i_document_parser.py`
  - `src/modules/knowledge/domain/events/document_attached_event.py`
- **Estimated scope:** Small (2 files)

---

### Task 4: Atualizar `KnowledgeBaseAggregate`
- **Description:** Atualizar `KnowledgeBaseAggregate.attach_document` e seu event applier `_apply_document_attached_event` para persistir `enable_ocr` e `ocr_instructions` no estado interno do documento.
- **Acceptance criteria:**
  - [x] `attach_document` aceita `enable_ocr: bool = False` e `ocr_instructions: str | None = None`.
  - [x] O dicionário `documents[doc_id]` armazena as preferências de OCR.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/modules/knowledge/domain/test_knowledge_base_aggregate.py`
- **Dependencies:** Task 3
- **Files touched:**
  - `src/modules/knowledge/domain/aggregates/knowledge_base_aggregate.py`
- **Estimated scope:** Small (1 file)

---

## Checkpoint 2: Domain Contracts Verified

---

## Phase 3: Application Layer & MarkItDown Adapter

### Task 5: Refatorar `MarkItDownDocumentParser`
- **Description:** Atualizar `MarkItDownDocumentParser` para suportar o modo nativo rápido (quando `enable_ocr=False`) e o modo multimodal com OpenRouter (quando `enable_ocr=True`), injetando `llm_prompt` customizado ou padrão.
- **Acceptance criteria:**
  - [x] `parse_to_markdown` executa fast-path em CPU quando `enable_ocr=False`.
  - [x] `parse_to_markdown` utiliza o `MarkItDown` com `llm_client` e `llm_prompt` quando `enable_ocr=True`.
  - [x] Fallback gracioso para decodificação textual em caso de falha.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/modules/knowledge/infrastructure/test_markitdown_document_parser.py`
- **Dependencies:** Task 2, Task 3
- **Files touched:**
  - `src/modules/knowledge/infrastructure/adapters/markitdown_document_parser.py`
- **Estimated scope:** Small (1 file)

---

### Task 6: Atualizar Use Case e Saga Coordinator
- **Description:** Atualizar `AttachAndStoreDocumentRequest` e `AttachAndStoreDocumentUseCase` para receber `enable_ocr` e `ocr_instructions`. Atualizar `DocumentIngestionSagaCoordinator.handle_document_stored` para ler esses campos de `kb.documents[event.document_id]` e repassá-los ao `_parser.parse_to_markdown`.
- **Acceptance criteria:**
  - [x] `AttachAndStoreDocumentRequest` contém `enable_ocr: bool = False` e `ocr_instructions: str | None = None`.
  - [x] A saga orquestra a chamada de parsing passando as opções configuradas pelo usuário.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/modules/knowledge/application/`
- **Dependencies:** Task 4, Task 5
- **Files touched:**
  - `src/modules/knowledge/application/use_cases/attach_and_store_document/attach_and_store_document_request.py`
  - `src/modules/knowledge/application/use_cases/attach_and_store_document/attach_and_store_document_use_case.py`
  - `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`
- **Estimated scope:** Medium (3 files)

---

## Checkpoint 3: Application & Parsing Layer Ready

---

## Phase 4: API Gateway & Dependency Injection

### Task 7: Atualizar Endpoint de Upload e Container
- **Description:** Atualizar o endpoint `POST /api/v1/knowledge/bases/{kb_id}/documents` em `knowledge_controller.py` para aceitar `enable_ocr: bool = Form(default=False)` e `ocr_instructions: str | None = Form(default=None)`. Atualizar `create_app_container` em `container.py` para instanciar o `MarkItDownDocumentParser` com o cliente OpenRouter configurado.
- **Acceptance criteria:**
  - [x] O controller aceita os novos campos via `Form(...)` com defaults seguros.
  - [x] `AppContainer` conecta a factory do OpenRouter ao `MarkItDownDocumentParser`.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/test_api_gateway.py`
- **Dependencies:** Task 6
- **Files touched:**
  - `src/api_gateway/controllers/knowledge_controller.py`
  - `src/api_gateway/container.py`
- **Estimated scope:** Small (2 files)

---

## Checkpoint 4: Backend API Ready

---

## Phase 5: Frontend Console UI

### Task 8: Atualizar Tipos e Client API no Frontend
- **Description:** Atualizar `frontend/src/api/types.ts` e `frontend/src/api/knowledge-api.ts` para que `uploadDocument` aceite `enableOcr?: boolean` e `ocrInstructions?: string` e os anexe ao `FormData`.
- **Acceptance criteria:**
  - [x] Interface `UploadDocumentOptions` adicionada em `types.ts`.
  - [x] `knowledgeApi.uploadDocument` envia `enable_ocr` e `ocr_instructions` no FormData.
- **Verification:**
  - [x] Command: `cd frontend && npm run build`
- **Dependencies:** Task 7
- **Files touched:**
  - `frontend/src/api/types.ts`
  - `frontend/src/api/knowledge-api.ts`
  - `frontend/src/hooks/useKnowledgeBases.ts`
- **Estimated scope:** Small (3 files)

---

### Task 9: Atualizar Modal de Upload (`DocumentUploadModal.tsx`)
- **Description:** Adicionar ao `DocumentUploadModal.tsx` um switch/toggle moderno para habilitar OCR multimodal, com alerta de performance/custo e um campo expansível para customizar as instruções de estrutura Markdown.
- **Acceptance criteria:**
  - [x] Toggle visual "Habilitar OCR / Análise Visual (Imagens, Tabelas e Gráficos)".
  - [x] Banner explicativo: "Desativado por padrão para documentos de texto (processamento instantâneo com custo zero)."
  - [x] Textarea opcional para "Instruções de Estrutura Markdown".
  - [x] Envio das opções ao chamar a mutation de upload.
- **Verification:**
  - [x] Command: `cd frontend && npm run build`
- **Dependencies:** Task 8
- **Files touched:**
  - `frontend/src/pages/ingestion/DocumentUploadModal.tsx`
- **Estimated scope:** Small (1 file)

---

## Checkpoint 5: Frontend UI Verified

---

## Phase 6: Automated Tests & Pre-Commit Gate

### Task 10: Criar Testes Automatizados Abrangentes
- **Description:** Criar e atualizar testes unitários para o `MarkItDownDocumentParser`, `AttachAndStoreDocumentUseCase`, `DocumentIngestionSagaCoordinator` e controller de upload.
- **Acceptance criteria:**
  - [x] Teste unitário de parsing com `enable_ocr=False` garantindo que o client LLM não é chamado.
  - [x] Teste unitário de parsing com `enable_ocr=True` e `ocr_instructions` personalizadas.
  - [x] Teste de integração do endpoint HTTP enviando multipart form com opções de OCR.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/ -v`
- **Dependencies:** Tasks 1-9
- **Files touched:**
  - `tests/unit/modules/knowledge/infrastructure/test_markitdown_document_parser.py`
  - `tests/unit/modules/knowledge/application/test_attach_and_store_document_use_case.py`
- **Estimated scope:** Medium (2-3 files)

---

### Task 11: Execução dos Gates Oficiais (`make pre-commit`, `npm run build`)
- **Description:** Executar a suíte completa de lint, formatação, verificação estrita de tipagem (Mypy Strict) e build de produção do frontend.
- **Acceptance criteria:**
  - [x] `make pre-commit` com zero erros e zero warnings.
  - [x] `npm run build` no frontend com zero erros de TypeScript.
- **Verification:**
  - [x] Command: `make pre-commit`
- **Dependencies:** Task 10
- **Files touched:**
  - `CHANGELOG.md`
- **Estimated scope:** Small (1 file)

---

## Checkpoint 6: Feature Complete
- [x] Pipeline de OCR configurável com OpenRouter e MarkItDown totalmente integrado, testado e validado.
