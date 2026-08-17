# Task List: Frontend Console SPA & RAG Query Playground

## Phase 1: Backend Support Endpoints & Synthesis Service

### Task 1: List Knowledge Bases Use Case & Endpoint
- **Description:** Criar o caso de uso `ListKnowledgeBasesUseCase`, seus DTOs de request/response e expor a rota `GET /api/v1/knowledge/bases` no `knowledge_controller.py`.
- **Acceptance criteria:**
  - [x] `ListKnowledgeBasesUseCase` implementado com tipagem estrita e Result pattern.
  - [x] Rota `GET /api/v1/knowledge/bases` retorna lista de KBs com `id`, `name`, `description`, `status`, `storage_partition`, `documents_count`.
  - [x] Single Class per File respeitado rigorosamente.
- **Verification:**
  - [x] Tests pass: `uv run pytest tests/unit/test_list_knowledge_bases_use_case.py`
  - [x] Mypy: `uv run mypy src/modules/knowledge/ src/api_gateway/`
- **Dependencies:** None
- **Files likely touched:**
  - `src/modules/knowledge/application/use_cases/list_knowledge_bases/*`
  - `src/api_gateway/controllers/knowledge_controller.py`
  - `src/api_gateway/container.py`
- **Estimated scope:** Medium (3-5 files)

---

### Task 2: RAG Answer Synthesis & Enriched Query Endpoint
- **Description:** Implementar serviço/caso de uso de síntese RAG com Gemini Flash-Lite (`GeminiRagSynthesizer` / `InMemoryRagSynthesizer`) e atualizar o endpoint `POST /api/v1/knowledge/bases/{kb_id}/query` para retornar a resposta sintetizada (`answer`), chunks de evidência e subgrafos recuperados do FalkorDB.
- **Acceptance criteria:**
  - [x] `ILlmSynthesisService` protocol e adaptadores implementados para geração contextualizada via LLM.
  - [x] `QueryKnowledgeResponse` DTO enriquecido com campo `answer: str` e mantendo `results` (chunks + subgrafos).
  - [x] Tratamento de fallback caso nenhum contexto relevante seja encontrado.
- **Verification:**
  - [x] Tests pass: `uv run pytest tests/unit/test_query_knowledge_use_case.py`
- **Dependencies:** Task 1
- **Files likely touched:**
  - `src/modules/knowledge/application/use_cases/query_knowledge/*`
  - `src/modules/knowledge/domain/interfaces/i_llm_synthesis_service.py`
  - `src/modules/knowledge/infrastructure/adapters/gemini_rag_synthesizer.py`
  - `src/api_gateway/container.py`
- **Estimated scope:** Medium (4-5 files)

---

### Task 3: Backend Tests & Quality Gate
- **Description:** Adicionar testes de integração das novas rotas de API e executar o gate oficial `make pre-commit`.
- **Acceptance criteria:**
  - [x] Testes de API para `GET /api/v1/knowledge/bases` e `POST /api/v1/knowledge/bases/{kb_id}/query` passando.
  - [x] `make pre-commit` executado com 100% de sucesso (Ruff zero erros, Mypy strict zero erros, Pytest 100% passando).
- **Verification:**
  - [x] Command: `make pre-commit`
- **Dependencies:** Task 1, Task 2
- **Files likely touched:**
  - `tests/integration/test_api_gateway.py`
- **Estimated scope:** Small (1-2 files)

---

## Checkpoint: Backend Foundation
- [x] Rotas `GET /api/v1/knowledge/bases` e `POST /api/v1/knowledge/bases/{kb_id}/query` operacionais e validadas.
- [x] Gate `make pre-commit` passando com zero warnings/erros.

---

## Phase 2: Frontend Scaffolding & Core Design System

### Task 4: Setup do Projeto Frontend (Vite + React + TS + Tailwind)
- **Description:** Inicializar a estrutura modular da SPA em `/frontend` com Vite, React 18+, TypeScript, Tailwind CSS, Lucide React, Axios e TanStack React Query.
- **Acceptance criteria:**
  - [x] Diretório `/frontend` estruturado com `package.json`, `tsconfig.json`, `vite.config.ts`, `tailwind.config.js`, `postcss.config.js`.
  - [x] Cliente API configurado (`src/api/client.ts`) com base URL configurável via `VITE_API_URL`.
  - [x] Provedores de roteamento (`react-router-dom`) e `QueryClientProvider` configurados em `App.tsx` e `main.tsx`.
- **Verification:**
  - [x] Build succeeds: `cd frontend && npm run build`
- **Dependencies:** None
- **Files likely touched:**
  - `frontend/package.json`
  - `frontend/vite.config.ts`
  - `frontend/tailwind.config.js`
  - `frontend/src/main.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/index.css`
- **Estimated scope:** Medium (5 files)

---

### Task 5: Layout Base & Componentes Atômicos de UI
- **Description:** Construir o shell da aplicação (`Sidebar`, `Header`, `PageContainer`) e a biblioteca de componentes reutilizáveis acessíveis e estilizados com Tailwind CSS.
- **Acceptance criteria:**
  - [x] Componentes atômicos: `Button`, `Input`, `Textarea`, `Select`, `Card`, `Badge`, `Modal`, `Progress`, `EmptyState`, `ErrorBanner`.
  - [x] Shell de layout responsivo com menu lateral navegável para: Ontologias, Knowledge Bases e Playground.
  - [x] Single Component per File rigoroso no frontend.
- **Verification:**
  - [x] TypeScript check: `cd frontend && npm run type-check`
- **Dependencies:** Task 4
- **Files likely touched:**
  - `frontend/src/components/layout/*`
  - `frontend/src/components/ui/*`
  - `frontend/src/components/feedback/*`
- **Estimated scope:** Medium (5-8 files)

---

## Checkpoint: Frontend Scaffolding
- [x] Navegação e layout funcionais, tema limpo e componentes atômicos prontos.

---

## Phase 3: Vertical Slice: Gestão de Ontologias

### Task 6: Ontologies API Client, Types & React Query Hooks
- **Description:** Definir os contratos TypeScript para ontologias (`OntologyTemplate`, `NodeTypeDefinition`, `RelationshipTypeDefinition`), funções de chamada HTTP (`ontologies-api.ts`) e hooks React Query (`useOntologies`, `useCreateOntology`, `useOntologyDetail`).
- **Acceptance criteria:**
  - [x] Types estritos alinhados com os DTOs do backend.
  - [x] Funções API para `list`, `getById`, `create`.
  - [x] Hooks com refetch automático e invalidação de cache pós-mutação.
- **Verification:**
  - [x] TypeScript check: `cd frontend && npm run type-check`
- **Dependencies:** Task 5
- **Files likely touched:**
  - `frontend/src/api/types.ts`
  - `frontend/src/api/ontologies-api.ts`
  - `frontend/src/hooks/useOntologies.ts`
- **Estimated scope:** Small (3 files)

---

### Task 7: Páginas de Listagem, Criação Estruturada e Detalhe de Ontologia
- **Description:** Construir as páginas para gerenciar ontologias: tabela com busca (`OntologiesListPage`), formulário dinâmico de cadastro de entidades e relações (`CreateOntologyPage`) e visualizador de detalhes com preview JSON (`OntologyDetailPage`).
- **Acceptance criteria:**
  - [x] `CreateOntologyPage` permite adicionar/remover dinamicamente tipos de nós (nome, descrição, propriedades) e relações (origem, destino, verbo).
  - [x] `OntologiesListPage` lista ontologias cadastradas com contagem de nós/arestas.
  - [x] Feedback visual de sucesso/erro ao salvar.
- **Verification:**
  - [x] Build & Type check: `cd frontend && npm run build`
- **Dependencies:** Task 6
- **Files likely touched:**
  - `frontend/src/pages/ontologies/OntologiesListPage.tsx`
  - `frontend/src/pages/ontologies/CreateOntologyPage.tsx`
  - `frontend/src/pages/ontologies/OntologyDetailPage.tsx`
- **Estimated scope:** Medium (3-4 files)

---

## Checkpoint: Ontologies Module
- [x] Criação e listagem de ontologias funcionando ponta a ponta na UI com backend integrado.

---

## Phase 4: Vertical Slice: Knowledge Bases, Upload & Monitor de Pipeline

### Task 8: Gestão de Knowledge Bases (Listagem, Criação e Detalhes)
- **Description:** Implementar a API de KBs (`knowledge-api.ts`), hook `useKnowledgeBases` e páginas `KnowledgeBasesListPage`, `CreateKnowledgeBasePage` (com seletor de ontologias e modal para criar ontologia inline) e `KnowledgeBaseDetailPage`.
- **Acceptance criteria:**
  - [x] `KnowledgeBasesListPage` exibe cards de KBs com métricas de documentos e status.
  - [x] `CreateKnowledgeBasePage` permite vincular ontologia existente ou abrir modal para criar nova ontologia sem perder dados do formulário.
  - [x] `KnowledgeBaseDetailPage` reúne visão geral, lista de documentos e atalho para upload e playground.
- **Verification:**
  - [x] Build & Type check: `cd frontend && npm run build`
- **Dependencies:** Task 7
- **Files likely touched:**
  - `frontend/src/api/knowledge-api.ts`
  - `frontend/src/hooks/useKnowledgeBases.ts`
  - `frontend/src/pages/knowledge-bases/KnowledgeBasesListPage.tsx`
  - `frontend/src/pages/knowledge-bases/CreateKnowledgeBasePage.tsx`
  - `frontend/src/pages/knowledge-bases/KnowledgeBaseDetailPage.tsx`
- **Estimated scope:** Medium (5 files)

---

### Task 9: Dropzone de Upload & Monitor Visual de Etapas do Pipeline
- **Description:** Implementar o modal de upload com drag & drop (`DocumentUploadModal`), o componente visual de etapas do pipeline (`PipelineStatusTracker`), o drawer de métricas e o hook de polling inteligente (`usePipelineMonitor`).
- **Acceptance criteria:**
  - [x] Upload suporta múltiplos arquivos (PDF, TXT, MD, DOCX, JSON) com progresso de envio.
  - [x] `PipelineStatusTracker` exibe as fases da Saga em tempo real (Enfileirado ➔ Parsing ➔ Chunking ➔ Embedding ➔ Extração Ontológica ➔ Indexação ➔ Concluído).
  - [x] Polling suave a cada 2000ms que interrompe requisições automaticamente quando todos os documentos terminam.
  - [x] Métricas detalhadas e mensagens de erro visíveis.
- **Verification:**
  - [x] Build & Type check: `cd frontend && npm run build`
- **Dependencies:** Task 8
- **Files likely touched:**
  - `frontend/src/pages/ingestion/DocumentUploadModal.tsx`
  - `frontend/src/pages/ingestion/PipelineStatusTracker.tsx`
  - `frontend/src/hooks/usePipelineMonitor.ts`
- **Estimated scope:** Medium (4 files)

---

## Checkpoint: Knowledge Bases & Ingestion Flow
- [x] Criação de KB, upload de arquivos e monitoramento visual das etapas de processamento funcionando ponta a ponta.

---

## Phase 5: Vertical Slice: RAG Query Playground & Containerização

### Task 10: Playground de Consulta RAG com Síntese e Inspetor de Evidências
- **Description:** Implementar a interface de Playground interativo (`QueryPlaygroundView`), renderizador de resposta do LLM em Markdown (`AnswerView`), inspetor expansível de subgrafos e chunks (`EvidenceInspector`) e hook `useRagQuery`.
- **Acceptance criteria:**
  - [x] Usuário digita perguntas e ajusta parâmetros de busca (`top_k`).
  - [x] Resposta sintetizada pelo LLM renderizada com formatação rica.
  - [x] Inspetor de evidências exibe chunks recuperados com scores e entidades do FalkorDB associadas.
- **Verification:**
  - [x] Build & Type check: `cd frontend && npm run build`
- **Dependencies:** Task 9
- **Files likely touched:**
  - `frontend/src/pages/playground/QueryPlaygroundView.tsx`
  - `frontend/src/pages/playground/AnswerView.tsx`
  - `frontend/src/pages/playground/EvidenceInspector.tsx`
  - `frontend/src/hooks/useRagQuery.ts`
- **Estimated scope:** Medium (4 files)

---

### Task 11: Multi-Stage Dockerfile (Nginx Alpine) & Integração no Docker Compose
- **Description:** Criar `Dockerfile` multi-stage ultraleve para o frontend (Estágio 1: build com Node 20 Alpine; Estágio 2: runtime com `nginx:1.27-alpine`), configuração de SPA fallback e proxy reverso (`nginx.conf`) e adicionar o serviço `frontend` na porta 3000 no `docker/docker-compose.yml`.
- **Acceptance criteria:**
  - [x] Imagem Docker final com tamanho inferior a 25MB (`nginx:1.27-alpine`).
  - [x] `docker/docker-compose.yml` inclui o serviço `frontend` acessível em `http://localhost:3000`.
  - [x] Roteamento SPA (`try_files $uri $uri/ /index.html;`) e proxy de `/api/v1` funcionando sem erros 404 ao recarregar a página.
- **Verification:**
  - [x] Configuração validada no `docker-compose.yml` e `nginx.conf`
- **Dependencies:** Task 10
- **Files likely touched:**
  - `frontend/Dockerfile`
  - `frontend/nginx.conf`
  - `docker/docker-compose.yml`
- **Estimated scope:** Small (3 files)

---

### Task 12: Validação Integrada Ponta a Ponta & Pre-Commit Gate
- **Description:** Executar a suíte de testes unitários do frontend com Vitest, checar builds de produção e validar todo o backend via `make pre-commit`.
- **Acceptance criteria:**
  - [x] Testes unitários do frontend passando no Vitest (`npm run test`).
  - [x] Build de produção do frontend (`npm run build`) sem warnings ou erros.
  - [x] `make pre-commit` executado com 100% de sucesso.
- **Verification:**
  - [x] Frontend: `cd frontend && npm run test && npm run build`
  - [x] Backend: `make pre-commit`
- **Dependencies:** Task 11
- **Files likely touched:**
  - `frontend/tests/*`
- **Estimated scope:** Small (2-3 files)

---

## Checkpoint: Final Review & Self-Hosted Ready
- [x] Stack completa sobe via `docker-compose up -d --build`.
- [x] Fluxo ponta a ponta validado: Criar Ontologia ➔ Criar KB ➔ Subir Documentos ➔ Acompanhar Pipeline ➔ Fazer Pergunta no Playground RAG.
