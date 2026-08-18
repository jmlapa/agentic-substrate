# Implementation Plan: Marco 1.17 — Real-Time Telemetry Precision, Continuous Pipeline Transitions & Frontend Progress Polish

## Overview

Este plano endereça os pontos de UX e precisão de telemetria identificados na interface gráfica durante a ingestão de documentos:

1. **Remoção de referências estáticas fora de ordem no OCR:** Substituir a mensagem `"Página {page_num} de {total_pages} processada..."` por um status limpo baseado exclusivamente no contador acumulado concluído (`"Processando OCR: {cur}/{total_pages} páginas concluídas"`).
2. **Cálculo de Percentual Estrito:** Garantir que o percentual de progresso nunca atinja $100\%$ em nenhuma etapa antes que todas as unidades daquela etapa tenham sido efetivamente concluídas (evitando que `round(436/437 * 100)` atinja $100\%$ na penúltima página).
3. **Eliminação da Barra Fantasma / Congelamento entre Etapas:** Emitir eventos de progresso imediatos no início de cada transição da Saga (`CHUNKING`, `GRAPH_EXTRACTION`, `EMBEDDINGS`) e atualizar o Projector para sincronizar mensagens nas etapas `PARSED`, `CHUNKED` e `INDEXED`, evitando que a barra de OCR fique visível durante o chunking e o tempo de espera da LLM.
4. **Polimento Visual no Frontend (`PipelineStatusTracker`):** Formatação consistente dos textos, badges numéricos, animações de carregamento e transição limpa para estado final indexado.

---

## Architecture Decisions

- **ADR-1: Mensagens Monotônicas Baseadas em Agregação:** Nenhuma mensagem descritiva de progresso deve interpolar variáveis de índice local de workers paralelos. Todas as mensagens devem derivar exclusivamente de `cur` (itens concluídos) e `tot` (total de itens).
- **ADR-2: Fórmula de Teto Estrito de Percentual ($99\%$ Guard):**
  $$\text{percentage} = \begin{cases} 100 & \text{se } cur = tot \\ \min(99, \lfloor \frac{cur}{\max(1, tot)} \times 100 \rfloor) & \text{se } cur < tot \end{cases}$$
- **ADR-3: Telemetria Imediata em Transições Síncronas/Assíncronas:** Ao entrar em cada handler de evento na Saga (`handle_document_parsed`, `handle_document_chunked`, `handle_graph_extracted`), publicar imediatamente um `DocumentProgressUpdatedEvent` com `current=0` e mensagem contextual de início da etapa, garantindo feedback visual instantâneo ao usuário enquanto a CPU ou a LLM preparam o lote.
- **ADR-4: Sincronização Explícita no Read Model (Projector):** Os handlers `handle_document_parsed`, `handle_document_chunked` e `handle_knowledge_indexed` devem atualizar explicitamente as colunas de telemetria no PostgreSQL para evitar retenção de mensagens desatualizadas de etapas anteriores.

---

## Dependency Graph & Implementation Order

```
Phase 1: Backend Telemetry Precision & Message Cleansing
  ├── ParallelVlmDocumentParser (Clean Monotonic OCR Message)
  └── Saga Coordinator & ToC (Strict Percentage Calculation Helper)
        │
        ▼
Phase 2: Continuous Pipeline Transitions & Read Model Projections
  ├── DocumentIngestionSagaCoordinator (Instant Transition Progress Events)
  └── KnowledgeBaseProjector (Transitional Projections for PARSED, CHUNKED & INDEXED)
        │
        ▼
Phase 3: Frontend Progress & Lifecycle Polish
  ├── PipelineStatusTracker.tsx (Clean Label, Percentage Badge, Smooth Transitions)
  └── Frontend Build Verification (Vite build)
        │
        ▼
Phase 4: Quality Gates & Specifications
  ├── Automated Tests (Unit & Integration)
  ├── make pre-commit (Ruff, Mypy Strict, Pytest)
  └── Specifications & Changelog Updates
```

---

## Task List

### Phase 1: Backend Telemetry Precision & Message Cleansing

- [ ] **Task 1: Sanitize OCR Progress Message & Strict Ceiling Percentage**
  - **Description:** No `ParallelVlmDocumentParser`, substituir a interpolação de `page_num` pela contagem acumulada. No `DocumentIngestionSagaCoordinator` e extratores, aplicar a fórmula estrita de percentual com teto de $99\%$ para itens incompletos.
  - **Files:**
    - `src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py`
    - `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`
  - **Acceptance criteria:**
    - Mensagem de OCR formatada como: `"Processando OCR: {cur}/{total_pages} páginas concluídas"`.
    - Percentual nunca é $100\%$ enquanto $cur < tot$.
  - **Verification:** `uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v`

### Phase 2: Continuous Pipeline Transitions & Read Model Projections

- [ ] **Task 2: Emit Instant Telemetry Events on Saga Transitions**
  - **Description:** Emitir eventos de progresso imediatos nos inícios das etapas de Chunking, Extração de Grafo e Embeddings no coordenador da Saga.
  - **Files:**
    - `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`
  - **Acceptance criteria:**
    - Ao entrar em `handle_document_parsed`, emite progresso da etapa `CHUNKING`.
    - Ao entrar em `handle_document_chunked`, emite progresso inicial `0/{total_parents}` da etapa `GRAPH_EXTRACTION`.
    - Ao entrar em `handle_graph_extracted`, emite progresso inicial `0/{total_children}` da etapa `EMBEDDINGS`.
  - **Verification:** `uv run pytest tests/integration/test_document_ingestion_saga_coordinator.py -v`

- [ ] **Task 3: Update Read Model Projections for Clean Transitional State**
  - **Description:** Atualizar o `KnowledgeBaseProjector` para sincronizar `progress_step`, `progress_percentage` e `progress_message` nos handlers de ciclo de vida (`handle_document_parsed`, `handle_document_chunked` e `handle_knowledge_indexed`).
  - **Files:**
    - `src/modules/knowledge/infrastructure/projections/knowledge_base_projector.py`
  - **Acceptance criteria:**
    - Transição para `PARSED` zera percentual e atualiza mensagem para `"Documento convertido em Markdown"`.
    - Transição para `CHUNKED` exibe resumo `"Chunks hierárquicos gerados: {parents} pais, {children} filhos"`.
    - Transição para `INDEXED` define percentual em $100\%$ e mensagem `"Processamento concluído com sucesso"`.
  - **Verification:** `uv run pytest tests/unit/test_projector_progress_telemetry.py -v`

### Phase 3: Frontend Progress & Lifecycle Polish

- [ ] **Task 4: Frontend PipelineStatusTracker Telemetry Polish**
  - **Description:** Refinar o componente `PipelineStatusTracker.tsx` para apresentar mensagens limpas, badge numérico condicional e transições suaves de layout.
  - **Files:**
    - `frontend/src/pages/ingestion/PipelineStatusTracker.tsx`
  - **Acceptance criteria:**
    - Texto descritivo principal limpo com ícone de spinner animado.
    - Badge de contagem `{pct}% ({cur}/{tot})` visível somente quando `tot > 0`.
    - Ocultação suave da barra granular quando o documento atinge status `INDEXED`.
  - **Verification:** `npm run build` na pasta `frontend/`

### Phase 4: Quality Gates & Verification

- [ ] **Task 5: Execute Quality Gates & Update Specifications**
  - **Description:** Executar `make pre-commit`, verificar zero erros e atualizar `SPEC-frontend-console.md`, `SPEC-resilient-saga-reprocessing-and-job-queues.md` e `CHANGELOG.md`.
  - **Acceptance criteria:**
    - `make pre-commit` com 100% de aprovação (Ruff, Mypy strict, Pytest).
    - `npm run build` do frontend bem-sucedido.
    - Documentações de especificações e changelog atualizados.
  - **Verification:** `make pre-commit`

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Corrida de eventos no Event Bus ao publicar múltiplos updates rápidos | Baixo | Cláusula SQL `GREATEST` no Projector e eventos ordenados por versão no banco |
| Polling do frontend capturar step transicional com `total = 0` | Baixo | Tratamento defensivo no frontend exibindo apenas a mensagem textual quando `progressTotal <= 0` |
| Sobrescrita indevida de mensagem de erro caso ocorra falha no chunking | Médio | Handlers de erro sempre sobrepõem qualquer mensagem de progresso com status `FAILED` |
