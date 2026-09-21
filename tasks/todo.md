# Task List: MCP Agent Connect Hub (Marco 1.23)

> **Regra de ouro:** Implement → Test → Verify (passing) → Commit.
> Cada tarefa deve ter escopo atômico, critérios de aceitação testáveis e verificação explícita.

---

## Tasks

### Task 1: Implementar DTOs e Endpoint de Introspecção `GET /api/v1/mcp/info` no Backend

**Description:** Cria os DTOs isolados no padrão Single Class per File em `src/api_gateway/dtos/` (`McpToolParameterDTO`, `McpToolInfoDTO`, `McpInfoResponseDTO`) e o controller `mcp_controller.py` em `src/api_gateway/controllers/`, registrando a rota `/api/v1/mcp/info` no FastAPI.

**Acceptance criteria:**
- [x] `src/api_gateway/dtos/mcp_tool_parameter_dto.py` criado com schema Pydantic v2.
- [x] `src/api_gateway/dtos/mcp_tool_info_dto.py` criado com schema Pydantic v2.
- [x] `src/api_gateway/dtos/mcp_info_response_dto.py` criado com schema Pydantic v2.
- [x] `src/api_gateway/dtos/__init__.py` exporta os novos DTOs.
- [x] `src/api_gateway/controllers/mcp_controller.py` implementa `GET /api/v1/mcp/info` introspectando as ferramentas ativas (`knowledge_query`, `knowledge_list_kbs`, `knowledge_search_notes`).
- [x] `src/api_gateway/controllers/__init__.py` exporta o router.
- [x] `src/api_gateway/main.py` registra o router no app FastAPI.

**Verification:**
```bash
uv run mypy --strict src/api_gateway/
uv run ruff check src/api_gateway/
```

**Files touched:**
- `src/api_gateway/dtos/mcp_tool_parameter_dto.py`
- `src/api_gateway/dtos/mcp_tool_info_dto.py`
- `src/api_gateway/dtos/mcp_info_response_dto.py`
- `src/api_gateway/dtos/__init__.py`
- `src/api_gateway/controllers/mcp_controller.py`
- `src/api_gateway/controllers/__init__.py`
- `src/api_gateway/main.py`

**Commit:** `feat(api_gateway): add mcp introspection endpoint and dtos`

---

### Task 2: Implementar Testes Unitários para o Endpoint `GET /api/v1/mcp/info`

**Description:** Cria testes unitários e de integração leve em `tests/unit/api_gateway/test_mcp_controller.py` validando o retorno do endpoint, presença de todas as tools registradas, schemas de parâmetros e status `online`.

**Acceptance criteria:**
- [x] Teste validando status HTTP 200 e schema de resposta `McpInfoResponseDTO`.
- [x] Teste verificando que `tools` contém `knowledge_query`, `knowledge_list_kbs` e `knowledge_search_notes`.
- [x] Teste verificando presença e tipos dos parâmetros de cada ferramenta.
- [x] 100% de aprovação nos testes unitários.

**Verification:**
```bash
uv run pytest tests/unit/api_gateway/test_mcp_controller.py -v
```

**Files touched:**
- `tests/unit/api_gateway/test_mcp_controller.py`

**Commit:** `test(api_gateway): add unit tests for mcp info endpoint`

---

### Task 3: Configurar Proxy Vite, Cliente de API e Hook TanStack Query no Frontend

**Description:** Adiciona `/mcp` ao proxy do Vite em `frontend/vite.config.ts`, cria as interfaces TypeScript e funções de API em `frontend/src/api/mcp-api.ts`, e cria o hook `useMcpInfo` com refetching intervalado em `frontend/src/hooks/useMcpInfo.ts`.

**Acceptance criteria:**
- [x] `frontend/vite.config.ts` possui proxy configurado para `/mcp`.
- [x] `frontend/src/api/mcp-api.ts` criado com tipos `McpToolParameter`, `McpToolInfo`, `McpInfoResponse` e função `getMcpInfo()`.
- [x] `frontend/src/hooks/useMcpInfo.ts` implementa hook com TanStack React Query (`queryKey: ['mcp-info']`, `refetchInterval: 10000`).

**Verification:**
```bash
cd frontend && npm run build
```

**Files touched:**
- `frontend/vite.config.ts`
- `frontend/src/api/mcp-api.ts`
- `frontend/src/hooks/useMcpInfo.ts`

**Commit:** `feat(frontend): setup mcp api client, vite proxy and react query hook`

---

### Task 4: Criar Componentes de UI Básicos: Snippet de Código, Banner de Saúde e Catálogo de Tools

**Description:** Implementa os componentes modulares: `McpCodeSnippet.tsx` (bloco de código com botão de cópia), `McpHealthBanner.tsx` (indicador de status online, contagem de tools e resolução de URL editável), e `McpToolsCatalog.tsx` (listagem dinâmica das ferramentas ativas com parâmetros e badges).

**Acceptance criteria:**
- [x] `frontend/src/pages/mcp/components/McpCodeSnippet.tsx` criado com feedback de cópia em 2s.
- [x] `frontend/src/pages/mcp/components/McpHealthBanner.tsx` criado com detecção inteligente de URL (`localhost:8000` vs produção) e indicador visual verde/vermelho.
- [x] `frontend/src/pages/mcp/components/McpToolsCatalog.tsx` criado renderizando cards para `knowledge_query`, `knowledge_list_kbs` e `knowledge_search_notes` com parâmetros detalhados.

**Verification:**
```bash
cd frontend && npm run build
```

**Files touched:**
- `frontend/src/pages/mcp/components/McpCodeSnippet.tsx`
- `frontend/src/pages/mcp/components/McpHealthBanner.tsx`
- `frontend/src/pages/mcp/components/McpToolsCatalog.tsx`

**Commit:** `feat(frontend): create mcp health banner, code snippet and tools catalog components`

---

### Task 5: Implementar Seletor de Agentes com as 10 Variantes Homologadas

**Description:** Implementa `McpClientSelectorTabs.tsx` com as abas e formatos oficiais estritamente pesquisados: Cursor, Claude Desktop, Claude Code, GitHub Copilot, Antigravity CLI, Gemini CLI, OpenCode, ChatGPT, Python SDK e Node.js SDK.

**Acceptance criteria:**
- [x] Abas para todos os 10 clientes com ícones/badges apropriados.
- [x] Cada aba exibe: Caminho de arquivo recomendado no SO, comando CLI (se aplicável), e snippet JSON/código válido com a URL dinâmica.
- [x] Aba GitHub Copilot utiliza especificamente a chave `"servers"`.
- [x] Aba Antigravity CLI utiliza especificamente `"serverUrl"`.
- [x] Aba OpenCode utiliza `"mcp": { "servers": { ... "type": "remote" } }`.

**Verification:**
```bash
cd frontend && npm run build
```

**Files touched:**
- `frontend/src/pages/mcp/components/McpClientSelectorTabs.tsx`

**Commit:** `feat(frontend): implement mcp client selector tabs for top 10 agents`

---

### Task 6: Montar a Página Principal do Hub e Integrar Roteamento e Sidebar

**Description:** Cria `McpConnectHubPage.tsx` orquestrando os componentes, adiciona a rota `/mcp` em `frontend/src/App.tsx`, e adiciona o item de navegação "Substrate MCP" com badge na `frontend/src/components/layout/Sidebar.tsx`.

**Acceptance criteria:**
- [x] `frontend/src/pages/mcp/McpConnectHubPage.tsx` renderiza layout completo e fluido.
- [x] `frontend/src/App.tsx` possui rota `/mcp` apontando para `McpConnectHubPage`.
- [x] `frontend/src/components/layout/Sidebar.tsx` exibe "Substrate MCP" com badge "v0.8.0" / "SSE" e ícone condizente.
- [x] Navegação funcional e sem quebras de layout no tema Dark.

**Verification:**
```bash
cd frontend && npm run build
```

**Files touched:**
- `frontend/src/pages/mcp/McpConnectHubPage.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/layout/Sidebar.tsx`

**Commit:** `feat(frontend): assemble mcp connect hub page and update sidebar navigation`

---

### Task 7: Validação Completa de Qualidade (`make pre-commit`) e Sincronização

**Description:** Executa todos os linters, formatadores, Mypy estrito, suíte de testes completa do backend e build do frontend.

**Acceptance criteria:**
- [x] `ruff check .` com zero erros.
- [x] `ruff format --check .` 100% formatado.
- [x] `mypy --strict src/ tests/` com `No issues found`.
- [x] `pytest` passando com mais de 244 testes.
- [x] `cd frontend && npm run build` gerando bundle de produção sem avisos ou erros.
- [x] `make pre-commit` aprovado com sucesso.

**Verification:**
```bash
make pre-commit
```

**Files touched:**
- Todos os arquivos modificados/criados

**Commit:** `chore(mcp): complete quality gates for mcp connect hub`
