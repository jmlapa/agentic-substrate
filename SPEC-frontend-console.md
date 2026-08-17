# Spec: Frontend Console SPA & RAG Query Playground (Agentic Substrate)

## Objective
Prover uma interface gráfica moderna, leve e funcional (SPA em `/frontend`) para o **Agentic Substrate**, permitindo a gestão visual completa do ciclo de vida de Knowledge Bases: criação de ontologias estruturadas avulsas/reutilizáveis, provisionamento de KBs, upload de documentos, monitoramento por etapas do pipeline de ingestão GraphRAG (com métricas de nós/arestas) e um Playground de consulta RAG interativo com síntese de respostas via LLM.

---

### User Stories & Comportamentos Esperados

1. **Gestão de Ontologias Reutilizáveis:**
   - O usuário pode criar ontologias de domínio independentes de qualquer KB através de um formulário estruturado simples.
   - O formulário permite cadastrar tipos de entidades (nome, descrição, propriedades/atributos) e tipos de relacionamentos (origem, destino, verbo/relação e descrição).
   - A listagem exibe todas as ontologias cadastradas com resumo de entidades e relações.
   - Uma visualização detalhada permite inspecionar o schema da ontologia e seu equivalente JSON.

2. **Criação e Gestão de Knowledge Bases:**
   - O usuário pode visualizar a listagem de todas as KBs existentes com status, partição de storage e quantidade de documentos.
   - Ao criar uma nova KB (nome, descrição), o usuário pode:
     a) Selecionar uma ontologia previamente cadastrada no dropdown;
     b) Criar uma nova ontologia inline via modal/drawer sem perder o contexto do formulário da KB.
   - Detalhes da KB exibem a ontologia vinculada, documentos indexados e ações rápidas (upload, monitoramento, playground).

3. **Upload de Documentos e Monitoramento de Pipeline:**
   - O usuário pode enviar múltiplos arquivos (PDF, TXT, MD, DOCX) com drag & drop.
   - A interface exibe a lista de arquivos com progresso em tempo real / polling regular (1.5s - 3s) refletindo as etapas da Saga assíncrona:
     - `PENDING` / `ENFILEIRADO` (Arquivo salvo no Storage local)
     - `PARSING` (Extração de texto MarkItDown)
     - `CHUNKING` (Structure-Tolerant Markdown Chunking com Parent/Child)
     - `EMBEDDING` (Geração de vetores Gemini MRL 768d)
     - `GRAPH_EXTRACTION` (PydanticAI LLM Extractor com Rate Limiter)
     - `INDEXING` (Persistência no FalkorDB e índices vetoriais)
     - `COMPLETED` / `FAILED`
   - O usuário pode expandir um documento para ver métricas detalhadas: tempo decorrido, número de chunks gerados, total de nós e arestas extraídos, e mensagem detalhada de erro caso falhe.

4. **Playground de Consulta RAG Interativo:**
   - Aba/tela de consulta dedicada para a KB selecionada.
   - O usuário digita uma pergunta e configura `top_k` de chunks/subgrafos.
   - O frontend envia a requisição para o endpoint de query que executa a busca híbrida GraphRAG + síntese de resposta com LLM.
   - A interface exibe:
     - **Resposta Sintetizada:** Texto gerado pelo LLM respondendo à pergunta com base estrita no contexto.
     - **Evidências Recuperadas:** Painel expansível com os chunks de texto textuais utilizados e os subgrafos/nós ontológicos retornados pelo FalkorDB com seus scores de similaridade.

5. **Ajustes de API no Backend (Fechamento do Ciclo RAG):**
   - Implementar `GET /api/v1/knowledge/bases` para listagem de KBs com métricas agregadas.
   - Expandir `POST /api/v1/knowledge/bases/{kb_id}/query` (ou endpoint especializado de RAG) para acoplar uma camada de síntese LLM (via Gemini Flash-Lite) retornando `answer` estruturada junto aos nós e chunks de contexto.
   - Garantir suporte a CORS amplo para desenvolvimento local e ambiente conteinerizado.

---

## Tech Stack & Architecture Decisions (Decisões Fechadas)

### Frontend (`/frontend`)
- **Linguagem & Runtime:** TypeScript 5.5+, Node.js 20+ (Ambiente de build)
- **Framework & Bundler:** React 18.3.1 com Vite 5.4+ (Single Page Application pura)
- **Roteamento:** React Router DOM v6.26+
- **Estilização:** Tailwind CSS v3.4+ com tema Dark-first limpo e elegante (Slate/Zinc neutro + acentos em Indigo e Emerald)
- **Ícones:** Lucide React (v0.400+)
- **Gerenciamento de Estado & Requisições:** TanStack React Query v5.50+ (gerenciamento de cache, refetching e polling configurado para 2000ms com auto-stop em estados terminais) + Axios 1.7+
- **Formulários & Validação:** React Hook Form 7.52+ com Zod 3.23+
- **Web Server de Produção & Container:** **Nginx Alpine (`nginx:1.27-alpine`)** via Dockerfile multi-stage. Imagem final < 25MB, com fallback `try_files $uri $uri/ /index.html;` e proxy reverso para a API FastAPI.

### Backend Complementar (`src/api_gateway` e `src/modules/knowledge`)
- **Framework:** FastAPI (Python 3.12+)
- **Síntese RAG:** LLM Synthesis Service acoplado a `google-genai` usando **Gemini 2.5 Flash-Lite** (`gemini-2.5-flash-lite`) com temperatura `0.2` para respostas factuais e citadas.
- **Tipagem & Qualidade:** Mypy `strict = true`, Ruff, Single Class per File

---

## Commands

### Frontend
```bash
# Entrar no diretório frontend
cd frontend

# Instalação de dependências
npm install

# Execução em ambiente de desenvolvimento (com hot-reload)
npm run dev

# Checagem de tipagem TypeScript
npm run type-check

# Linter e formatação
npm run lint

# Execução de testes unitários (Vitest)
npm run test

# Build de produção
npm run build

# Preview da build local
npm run preview
```

### Docker & Full Stack
```bash
# Subir toda a infraestrutura com o novo container de frontend
docker-compose up -d --build

# Verificar logs do frontend
docker-compose logs -f frontend

# Acessar a aplicação
open http://localhost:3000
```

---

## Project Structure (Single Component / Class per File)

```
agentic-substrate/
├── docker-compose.yml                     # Serviço 'frontend' adicionado mapeando porta 3000 -> 80
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── Dockerfile                         # Multi-stage build ultra-leve (<25MB)
│   ├── nginx.conf                         # Configuração Nginx SPA fallback e reverse proxy
│   ├── src/
│   │   ├── main.tsx                       # Bootstrap React
│   │   ├── App.tsx                        # Layout principal e rotas
│   │   ├── index.css                      # Design tokens, tipografia e reset
│   │   ├── api/
│   │   │   ├── client.ts                  # Instância Axios com base URL e interceptors
│   │   │   ├── ontologies-api.ts          # Chamadas REST para /api/v1/ontologies
│   │   │   ├── knowledge-api.ts           # Chamadas REST para /api/v1/knowledge/bases
│   │   │   └── types.ts                   # Interfaces e tipos compartilhados dos contratos DTO
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx             # Barra superior de navegação
│   │   │   │   ├── Sidebar.tsx            # Navegação lateral (Ontologias, KBs, Monitor, Playground)
│   │   │   │   └── PageContainer.tsx      # Wrapper padrão de página com títulos e breadcrumbs
│   │   │   ├── ui/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Textarea.tsx
│   │   │   │   ├── Select.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Badge.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Progress.tsx
│   │   │   │   └── Toast.tsx
│   │   │   └── feedback/
│   │   │       ├── LoadingSpinner.tsx
│   │   │       ├── EmptyState.tsx
│   │   │       └── ErrorBanner.tsx
│   │   ├── pages/
│   │   │   ├── ontologies/
│   │   │   │   ├── OntologiesListPage.tsx # Tabela de ontologias existentes com filtros
│   │   │   │   ├── CreateOntologyPage.tsx # Formulário guiado para nova ontologia
│   │   │   │   └── OntologyDetailPage.tsx # Inspeção de nós, arestas e JSON schema
│   │   │   ├── knowledge-bases/
│   │   │   │   ├── KnowledgeBasesListPage.tsx # Grid/Cards de KBs com métricas
│   │   │   │   ├── CreateKnowledgeBasePage.tsx # Formulário com seleção/criação inline de ontologia
│   │   │   │   └── KnowledgeBaseDetailPage.tsx # Dashboard da KB com abas: Documentos, Monitor e Playground
│   │   │   ├── ingestion/
│   │   │   │   ├── DocumentUploadModal.tsx     # Dropzone e upload com feedback imediato
│   │   │   │   ├── PipelineStatusTracker.tsx   # Visualizador de etapas (chips/stepper)
│   │   │   │   └── DocumentMetricsDrawer.tsx   # Detalhes de chunks, nós e arestas extraídos
│   │   │   └── playground/
│   │   │       ├── QueryPlaygroundView.tsx    # Interface de chat/pergunta com painel de contexto
│   │   │       ├── AnswerView.tsx             # Renderizador da resposta do LLM com markdown
│   │   │       └── EvidenceInspector.tsx      # Inspetor de chunks e subgrafos FalkorDB
│   │   └── hooks/
│   │       ├── useOntologies.ts               # Hooks React Query para ontologias
│   │       ├── useKnowledgeBases.ts           # Hooks React Query para KBs
│   │       ├── usePipelineMonitor.ts          # Hook de polling resiliente para status de documentos
│   │       └── useRagQuery.ts                 # Mutation hook para submissão de query RAG
│   └── tests/
│       ├── setup.ts
│       └── components/                        # Testes unitários com Vitest
└── src/ (Backend)
    ├── api_gateway/
    │   ├── controllers/
    │   │   └── knowledge_controller.py        # Adicionar endpoint GET /bases (list) e refinar /query
    │   └── dtos/
    │       ├── list_knowledge_bases_response_dto.py
    │       └── rag_query_response_dto.py
    └── modules/knowledge/
        └── application/use_cases/
            ├── list_knowledge_bases/          # Novo Caso de Uso para listagem de KBs
            └── synthesize_rag_answer/         # Caso de Uso de síntese RAG com LLM
```

---

## Code Style & Conventions

- **Componentes React Funcionais e Tipados:** Todo componente possui interface explícita para props.
- **Single Component per File:** Cada componente, hook ou serviço em seu próprio arquivo isolado.
- **Tratamento de Estado:** Uso de `isLoading`, `isError`, `data` fornecidos pelo React Query, com fallbacks acessíveis e amigáveis.
- **Design Clean e Utilitário:** Paleta neutra (Slate/Zinc) com cor primária de destaque (Indigo/Emerald). Sem gradientes poluídos ou sombras excessivas.

### Exemplo de Componente React (TypeScript + Tailwind)
```tsx
import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: LucideIcon;
  variant?: 'default' | 'success' | 'warning';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  description,
  icon: Icon,
  variant = 'default',
}) => {
  const variantStyles = {
    default: 'text-zinc-900 dark:text-zinc-100',
    success: 'text-emerald-600 dark:text-emerald-400',
    warning: 'text-amber-600 dark:text-amber-400',
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{title}</span>
        <div className="rounded-lg bg-zinc-100 p-2 dark:bg-zinc-800">
          <Icon className="h-5 w-5 text-zinc-600 dark:text-zinc-300" />
        </div>
      </div>
      <div className={`mt-3 text-2xl font-bold tracking-tight ${variantStyles[variant]}`}>
        {value}
      </div>
      {description && (
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{description}</p>
      )}
    </div>
  );
};
```

---

## Testing Strategy

- **Testes Unitários de Componentes:** Vitest + React Testing Library para testar comportamento de formulários (ex: adicionar e remover tipos de nós no criador de ontologias).
- **Testes de Integração de Hooks:** Testar `usePipelineMonitor` e `useRagQuery` com mocks de respostas da API.
- **Testes de API no Backend:** Pytest cobrindo os novos endpoints `GET /api/v1/knowledge/bases` e síntese de RAG `POST /api/v1/knowledge/bases/{kb_id}/query`.
- **Qualidade Contínua:** `make pre-commit` garantindo Mypy, Ruff e Pytest no backend, e `npm run type-check && npm run lint` no frontend.

---

## Boundaries

- **Always do:**
  - Tipar todas as props, retornos de hooks e respostas de API com TypeScript estrito.
  - Manter a regra de *Single Component / Single Class per File*.
  - Exibir feedback visual de carregamento e estados de erro em todas as ações assíncronas.
  - Testar requisições contra o backend real via Docker Compose e em mocks unitários.
  - Manter Dockerfile multi-stage enxuto (tamanho final < 25MB com Nginx Alpine).
- **Ask first:**
  - Adicionar bibliotecas externas pesadas no frontend (ex: frameworks de canvas 3D/WebGL).
  - Alterar contratos existentes de rotas de API do backend que possam quebrar clientes legados.
- **Never do:**
  - Introduzir dependência de autenticação obrigatória ou RBAC bloqueante na V1.
  - Usar `any` implícito ou explícito no TypeScript sem justificativa técnica extrema.
  - Hardcodar URLs da API no código (sempre utilizar variáveis de ambiente `VITE_API_URL`).

---

## Success Criteria

1. **Gestão de Ontologias:** É possível criar, listar e visualizar uma ontologia completa (com entidades e relações tipadas) pela UI e salvar no banco via API.
2. **Criação de KBs:** É possível criar uma KB selecionando uma ontologia existente ou criando uma nova ontologia diretamente no fluxo.
3. **Ingestão & Monitoramento:** O usuário faz upload de um arquivo PDF/TXT/MD na KB e visualiza a barra de status evoluir pelas etapas (`Enfileirado` ➔ `Parsing` ➔ `Chunking` ➔ `Extração de Grafo` ➔ `Indexação` ➔ `Concluído`) com contadores de nós/arestas gerados.
4. **Playground RAG:** O usuário submete uma pergunta no Playground e recebe uma resposta formatada sintetizada pelo LLM junto aos subgrafos e chunks de evidência recuperados do FalkorDB.
5. **Self-Hosted Ready:** Executar `docker-compose up` sobe todo o ecossistema (Postgres, FalkorDB, Redis, API FastAPI e Frontend Web na porta 3000) de forma funcional e integrada.
