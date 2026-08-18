# Task List: Marco 1.17 — Real-Time Telemetry Precision, Continuous Pipeline Transitions & Frontend Progress Polish

## Phase 1: Backend Telemetry Precision & Message Cleansing

- [x] **Task 1: Sanitize OCR Progress Message & Strict Ceiling Percentage**
  - **Description:** No `ParallelVlmDocumentParser`, substituir a interpolação de `page_num` pela contagem acumulada. No `DocumentIngestionSagaCoordinator` e extratores, aplicar a fórmula estrita de percentual com teto de $99\%$ para itens incompletos.
  - **Acceptance criteria:**
    - [x] Mensagem de OCR formatada como: `"Processando OCR: {cur}/{total_pages} páginas concluídas"`.
    - [x] Percentual nunca é $100\%$ enquanto $cur < tot$.
    - [x] 0 referências a `page_num` individual na mensagem de progresso do OCR.
  - **Verification:** `uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v`
  - **Files:** `src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py`, `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`

### Checkpoint: Phase 1
- [x] OCR unit tests passing with sanitized messages and strict percentage ceiling
- [x] Mypy strict & Ruff clean

---

## Phase 2: Continuous Pipeline Transitions & Read Model Projections

- [x] **Task 2: Emit Instant Telemetry Events on Saga Transitions**
  - **Description:** Emitir eventos de progresso imediatos nos inícios das etapas de Chunking, Extração de Grafo e Embeddings no coordenador da Saga.
  - **Acceptance criteria:**
    - [x] Ao entrar em `handle_document_parsed`, emite progresso da etapa `CHUNKING` (`current=0`, `total=1`, `percentage=0`, `message="Fatiando documento em Chunks Hierárquicos (Pai/Filho)..."`).
    - [x] Ao entrar em `handle_document_chunked`, emite progresso inicial `0/{total_parents}` da etapa `GRAPH_EXTRACTION`.
    - [x] Ao entrar em `handle_graph_extracted`, emite progresso inicial `0/{total_children}` da etapa `EMBEDDINGS`.
  - **Verification:** `uv run pytest tests/integration/test_document_ingestion_saga_coordinator.py -v`
  - **Files:** `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`

- [x] **Task 3: Update Read Model Projections for Clean Transitional State**
  - **Description:** Atualizar o `KnowledgeBaseProjector` para sincronizar `progress_step`, `progress_percentage` e `progress_message` nos handlers de ciclo de vida (`handle_document_parsed`, `handle_document_chunked` e `handle_knowledge_indexed`).
  - **Acceptance criteria:**
    - [x] Transição para `PARSED` zera percentual e atualiza mensagem para `"Documento convertido em Markdown"`.
    - [x] Transição para `CHUNKED` exibe resumo `"Chunks hierárquicos gerados: {parents} pais, {children} filhos"`.
    - [x] Transição para `INDEXED` define percentual em $100\%$ e mensagem `"Processamento concluído com sucesso"`.
  - **Verification:** `uv run pytest tests/unit/test_projector_progress_telemetry.py -v`
  - **Files:** `src/modules/knowledge/infrastructure/projections/knowledge_base_projector.py`

### Checkpoint: Phase 2
- [x] Integration and projection tests passing
- [x] Mypy strict & Ruff clean

---

## Phase 3: Frontend Progress & Lifecycle Polish

- [x] **Task 4: Frontend PipelineStatusTracker Telemetry Polish**
  - **Description:** Refinar o componente `PipelineStatusTracker.tsx` para apresentar mensagens limpas, badge numérico condicional e transições suaves de layout.
  - **Acceptance criteria:**
    - [x] Texto descritivo principal limpo com ícone de spinner animado.
    - [x] Badge de contagem `{pct}% ({cur}/{tot})` visível somente quando `tot > 0`.
    - [x] Ocultação suave da barra granular quando o documento atinge status `INDEXED`.
  - **Verification:** `npm run build` na pasta `frontend/`
  - **Files:** `frontend/src/pages/ingestion/PipelineStatusTracker.tsx`

### Checkpoint: Phase 3
- [x] Frontend builds cleanly with zero TypeScript / Vite errors

---

## Phase 4: Quality Gates & End-to-End Verification

- [x] **Task 5: Execute Quality Gates & Update Specifications**
  - **Description:** Executar `make pre-commit`, verificar zero erros e atualizar `SPEC-frontend-console.md`, `SPEC-resilient-saga-reprocessing-and-job-queues.md` e `CHANGELOG.md`.
  - **Acceptance criteria:**
    - [x] `make pre-commit` com 100% de aprovação (Ruff, Mypy strict, Pytest).
    - [x] `npm run build` do frontend bem-sucedido.
    - [x] Documentações de especificações e changelog atualizados.
  - **Verification:** `make pre-commit`
  - **Files:** `SPEC-frontend-console.md`, `SPEC-resilient-saga-reprocessing-and-job-queues.md`, `CHANGELOG.md`

### Checkpoint: Complete
- [x] All 5 tasks completed and verified
- [x] Ready for review
