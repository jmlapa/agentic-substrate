# Implementation Plan: Frontend Console SPA & RAG Query Playground

## Overview
Construir uma interface SPA moderna, leve e funcional no diretório `/frontend` (Vite, React 18+, TypeScript, Tailwind CSS, TanStack Query) integrada ao Agentic Substrate. A aplicação permitirá a gestão visual completa de ontologias estruturadas, criação e listagem de Knowledge Bases, upload de arquivos, monitoramento em tempo real por etapas do pipeline de ingestão GraphRAG e um Playground interativo de consultas RAG com síntese via LLM e inspeção de subgrafos FalkorDB.

---

## Architecture Decisions (Decisões Fechadas)

1. **Monorepo SPA Leve (`/frontend`)**:
   - **React 18.3.1 + Vite 5.4+ (TypeScript 5.5+)** para bundle estático SPA minificado e hot-reload instantâneo.
   - **Tailwind CSS 3.4+** com paleta Dark-first baseada em Zinc (`zinc-950` fundo, `zinc-900` cards, `zinc-800` bordas, `indigo-500`/`emerald-500` acentos).
   - **TanStack React Query v5.50+** para gerenciamento de cache de servidor, refetching automático e polling inteligente de status.
   - **React Hook Form 7.52+ + Zod 3.23+** para validação tipada estrita em tempo de formulário.
   - **Single Component per File** e tipagem estrita em TypeScript (sem `any`), alinhado com as diretrizes do repositório.

2. **Fechamento do Ciclo RAG no Backend (`api-gateway` e `knowledge`)**:
   - `GET /api/v1/knowledge/bases`: Endpoint para listar todas as KBs existentes com métricas agregadas (número de documentos, partição de storage e status).
   - `POST /api/v1/knowledge/bases/{kb_id}/query`: Atualização do endpoint de consulta para incorporar síntese de resposta com LLM via **Gemini 2.5 Flash-Lite** (`gemini-2.5-flash-lite`, temperatura `0.2`), retornando a resposta em Markdown formatado juntamente com as evidências (chunks e subgrafos FalkorDB recuperados).

3. **Estratégia de Monitoramento do Pipeline**:
   - Hook `usePipelineMonitor` com polling fixo de **2000ms (2s)** via React Query (`refetchInterval: 2000`).
   - Auto-stop condicional: o polling é pausado assim que 100% dos documentos da KB atingem estado terminal (`COMPLETED` ou `FAILED`).
   - Visualização por etapas da Saga: `ENFILEIRADO` ➔ `PARSING` ➔ `CHUNKING` ➔ `EMBEDDING` ➔ `EXTRAÇÃO DE GRAFO` ➔ `INDEXAÇÃO` ➔ `CONCLUÍDO`.

4. **Containerização & Servidor Web de Produção**:
   - **Nginx Alpine (`nginx:1.27-alpine`)** via Dockerfile multi-stage (estágio 1: build Node 20 alpine; estágio 2: runtime Nginx alpine).
   - Tamanho final da imagem < 25MB.
   - Configuração de fallback `try_files $uri $uri/ /index.html;` e proxy transparente de `/api/v1/` para o container do backend FastAPI.
   - Integração no `docker/docker-compose.yml` mapeando a porta 3000 para acesso direto ao console.

---

## Task List

### Phase 1: Backend Support Endpoints & Synthesis Service
- [ ] **Task 1: List Knowledge Bases Use Case & Endpoint**
  - Implementar caso de uso `ListKnowledgeBasesUseCase`, DTOs e rota `GET /api/v1/knowledge/bases`.
- [ ] **Task 2: RAG Answer Synthesis & Enriched Query Endpoint**
  - Implementar serviço/caso de uso de síntese com Gemini Flash-Lite e enriquecer `POST /api/v1/knowledge/bases/{kb_id}/query`.
- [ ] **Task 3: Backend Tests & Quality Gate**
  - Testes unitários para novos use cases e rotas. Validação com `make pre-commit`.

### Checkpoint: Backend Foundation
- [ ] Todos os testes do backend passando, tipagem Mypy strict 100% limpa, endpoints testados.

### Phase 2: Frontend Scaffolding & Core Design System
- [ ] **Task 4: Setup do Projeto Frontend (Vite + React + TS + Tailwind)**
  - Configurar `/frontend`, `package.json`, `tsconfig.json`, `vite.config.ts`, `tailwind.config.js`, `index.css` e cliente Axios/QueryClient.
- [ ] **Task 5: Layout Base & Componentes Atômicos de UI**
  - Criar `Sidebar`, `Header`, `PageContainer`, `Button`, `Input`, `Select`, `Card`, `Badge`, `Modal`, `Progress`, `EmptyState` e `Toast`.

### Checkpoint: Frontend Scaffolding
- [ ] Frontend compila sem erros de TypeScript, layout renderiza e navegação funciona.

### Phase 3: Vertical Slice: Gestão de Ontologias
- [ ] **Task 6: Ontologies API, Types e React Query Hooks**
  - Criar contratos TypeScript, chamadas de API (`ontologies-api.ts`) e hooks (`useOntologies.ts`).
- [ ] **Task 7: Páginas de Listagem, Criação Estruturada e Detalhe de Ontologia**
  - `OntologiesListPage.tsx`, `CreateOntologyPage.tsx` (com adição dinâmica de entidades/relações) e `OntologyDetailPage.tsx`.

### Checkpoint: Ontologies Module
- [ ] Usuário consegue criar ontologias estruturadas, listar e inspecionar detalhes via UI.

### Phase 4: Vertical Slice: Knowledge Bases, Upload & Monitor de Pipeline
- [ ] **Task 8: Gestão de Knowledge Bases (Listagem, Criação e Detalhes)**
  - `KnowledgeBasesListPage.tsx`, `CreateKnowledgeBasePage.tsx` (com seleção ou criação inline de ontologia) e `KnowledgeBaseDetailPage.tsx`.
- [ ] **Task 9: Dropzone de Upload & Monitor Visual de Etapas do Pipeline**
  - `DocumentUploadModal.tsx`, `PipelineStatusTracker.tsx` (stepper visual), `DocumentMetricsDrawer.tsx` e hook `usePipelineMonitor.ts`.

### Checkpoint: Knowledge Bases & Ingestion Flow
- [ ] Criação de KB, upload de arquivos e acompanhamento das etapas do pipeline em tempo real validados na UI.

### Phase 5: Vertical Slice: RAG Query Playground & Containerização
- [ ] **Task 10: Playground de Consulta RAG com Síntese e Inspetor de Evidências**
  - `QueryPlaygroundView.tsx`, `AnswerView.tsx` (markdown renderer), `EvidenceInspector.tsx` (chunks e subgrafos) e `useRagQuery.ts`.
- [ ] **Task 11: Multi-stage Dockerfile & Integração no Docker Compose**
  - Criar `/frontend/Dockerfile`, `/frontend/nginx.conf` e adicionar serviço `frontend` na porta 3000 no `docker-compose.yml`.
- [ ] **Task 12: Validação Integrada Ponta a Ponta & Pre-Commit Gate**
  - Execução dos gates de qualidade (testes frontend Vitest, `npm run build`, `make pre-commit`).

### Checkpoint: Final Review & Self-Hosted Ready
- [ ] Stack completa sobe com `docker-compose up`, fluxo ponta a ponta (Ontologia ➔ KB ➔ Upload ➔ Monitor ➔ Playground) 100% funcional.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Bloqueio de CORS entre frontend e API FastAPI | Médio | Configurar middleware de CORS permissivo no FastAPI para ambiente local e Docker. |
| Ingestão assíncrona longa em arquivos pesados | Médio | Implementar polling resiliente com backoff suave e indicadores visuais claros de status por fase. |
| Latência na síntese do LLM no endpoint de query | Baixo | Utilizar o Gemini Flash-Lite (`gemini-2.5-flash-lite`), com timeout configurado e loading state dedicado no Playground. |
| Payload de grafo muito grande para renderização | Baixo | Foco em visualização tabular/hierárquica estruturada de nós e arestas em vez de canvas 3D pesado na V1. |
