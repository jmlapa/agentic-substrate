# Implementation Plan: MCP Agent Connect Hub (Marco 1.23)

## 1. Overview

Disponibilizar no console web (`/frontend`) a central de integração **MCP Agent Connect Hub** (`/mcp`), permitindo a qualquer desenvolvedor ou construtor de agentes autônomos descobrir, configurar e validar o servidor MCP do Agentic Substrate para os 9 principais coding agents do mercado (Cursor, Claude Desktop, Claude Code, GitHub Copilot, Antigravity, Gemini CLI, OpenCode, ChatGPT, além de Python/Node SDKs), com verificador de saúde em tempo real e catálogo dinâmico de ferramentas cognitivas.

---

## 2. Architecture Decisions

- **Endpoint REST Introspectivo O(1):** Criar `GET /api/v1/mcp/info` no backend que inspeciona diretamente o `MCPServer` e retorna metadados estruturados das ferramentas registradas sem exigir conexões SSE persistentes do navegador.
- **Single Class per File & Strict Typing no Backend:** Todos os DTOs (`McpInfoResponseDTO`, `McpToolInfoDTO`, `McpToolParameterDTO`) e o controller (`mcp_controller.py`) em arquivos isolados, com validação Pydantic v2 e Mypy em modo estrito.
- **Detecção Inteligente de URL no Frontend:** Resolver automaticamente a URL do SSE (`http://localhost:8000/mcp/sse` quando rodando no Vite porta 3000 em dev, ou `window.location.origin + '/mcp/sse'` em produção com Caddy), permitindo edição rápida caso o usuário use túneis (ngrok).
- **Abas Fiéis à Documentação Oficial dos Agentes:** Cada cliente recebe sua aba formatada exatamente como sua documentação oficial exige (ex: `"servers"` no Copilot, `"serverUrl"` no Antigravity, `"type": "sse"` no Claude, `"type": "remote"` no OpenCode).
- **Vite Proxy Local para `/mcp`:** Adicionar `/mcp` ao `proxy` do `frontend/vite.config.ts` para paridade de desenvolvimento local.

---

## 3. Dependency Graph

```
[Task 1] Backend DTOs e Endpoint de Introspecção (GET /api/v1/mcp/info)
    │
    └── [Task 2] Testes Unitários e Integração do Backend (Mypy + Pytest)
            │
            └── [Task 3] Cliente de API e Hook TanStack Query no Frontend (useMcpInfo)
                    │
                    └── [Task 4] Componentes de UI (CodeSnippet, HealthBanner, ToolsCatalog)
                            │
                            └── [Task 5] Seletor de Agentes (McpClientSelectorTabs com 10 clientes)
                                    │
                                    └── [Task 6] Página Principal e Integração de Rotas/Sidebar
                                            │
                                            └── [Task 7] Validação dos Gates e Build Final (make pre-commit)
```

---

## 4. Phase Breakdown

### Phase 1: Backend Introspection API & Single Class per File (Tasks 1 & 2)
- Criação dos DTOs: `McpToolParameterDTO`, `McpToolInfoDTO`, `McpInfoResponseDTO` em `src/api_gateway/dtos/`.
- Criação do controller `mcp_controller.py` em `src/api_gateway/controllers/`.
- Registro da rota no `main.py`.
- Testes unitários com Pytest em `tests/unit/api_gateway/test_mcp_controller.py`.

### Phase 2: Frontend Data Layer & Core Components (Tasks 3 & 4)
- Configuração do proxy `/mcp` em `frontend/vite.config.ts`.
- Tipagens TypeScript e cliente Axios em `frontend/src/api/mcp-api.ts`.
- Hook TanStack React Query `useMcpInfo` com polling em `frontend/src/hooks/useMcpInfo.ts`.
- Componentes modulares `McpCodeSnippet.tsx`, `McpHealthBanner.tsx` e `McpToolsCatalog.tsx`.

### Phase 3: Agent Selector, Page Assembly & Navigation (Tasks 5 & 6)
- Componente `McpClientSelectorTabs.tsx` com as 10 variantes homologadas e 1-click copy.
- Montagem da página principal `McpConnectHubPage.tsx` em `frontend/src/pages/mcp/`.
- Adição da rota `/mcp` em `frontend/src/App.tsx` e link na `frontend/src/components/layout/Sidebar.tsx`.

### Phase 4: Verification & Quality Gates (Task 7)
- Verificação de compilação frontend (`npm run build`).
- Execução do gate oficial `make pre-commit` (Ruff, Mypy strict, Pytest com cobertura).

---

## 5. Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Diferença de portas entre Vite (3000) e FastAPI (8000) quebrar o snippet copiado | Alto | Lógica no `McpHealthBanner` que detecta hostname `localhost` e substitui a porta da UI (3000) pela da API (8000), permitindo também edição livre pelo usuário. |
| Inconsistência de schemas entre agentes (ex: Copilot usa `"servers"` em vez de `"mcpServers"`) | Alto | Cada aba tem gerador de JSON isolado, estritamente baseado nas documentações oficiais pesquisadas. |
| Violação da regra Single Class per File nos novos DTOs | Alto | Cada DTO em seu próprio arquivo dentro de `src/api_gateway/dtos/`. |
| Falha de Mypy strict no controller | Médio | Tipagem 100% explícita em todos os retornos e parâmetros de rotas. |
