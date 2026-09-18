# Implementation Plan: Streamable HTTP/SSE MCP Server (Marco 1.22)

## 1. Overview

Implementar a interface de **Model Context Protocol (MCP)** sobre **HTTP/SSE (Server-Sent Events)** no `api-gateway` do Agentic Substrate. A interface permitirá que agentes autônomos externos (Claude, Cursor, LangGraph, CrewAI, AutoGen) descubram e consumam as ferramentas cognitivas de recuperação do Substrate (`knowledge_query`, `knowledge_list_kbs`, `knowledge_search_notes`) de forma in-process, modular e com tipagem estrita.

---

## 2. Architecture Decisions

- **Servidor MCP Unificado na Borda:** Um único ponto de entrada SSE (`/mcp/sse` e `/mcp/messages`), eliminando a necessidade de múltiplos servidores e conexões paralelas no cliente MCP.
- **In-Process Invocation:** O servidor MCP chama diretamente os Use Cases em memória através do `AppContainer`, com 0ms de latência de rede adicional e sem necessidade de proxy HTTP intermediário.
- **Single Class per File & Modular Providers:** Cada ferramenta (`KnowledgeQueryTool`, etc.) e o provedor de ferramentas (`KnowledgeMcpToolProvider`) residem em seus próprios arquivos, seguindo rigorosamente o `AGENTS.md`.
- **Foco em Retrieval no MVP:** Operações de ingestão e mutação pesadas continuam na API REST (`multipart/form-data`), mantendo o MCP rápido, focado e imune a gargalos de payload binário sobre JSON-RPC.

---

## 3. Dependency Graph

```
[Task 1] Adicionar dependência 'mcp' no pyproject.toml
    │
    └── [Task 2] Protocolo IMcpToolProvider e Handlers das Tools (tools/ e protocols/)
            │
            └── [Task 3] Provedor Modular KnowledgeMcpToolProvider (providers/)
                    │
                    └── [Task 4] Servidor MCP e Gerenciador de Sessões SSE (mcp_server_app.py)
                            │
                            └── [Task 5] Integração no FastAPI (main.py) e Roteamento Proxy
                                    │
                                    └── [Task 6] Testes de Integração End-to-End MCP (SSE + JSON-RPC)
                                            │
                                            └── [Task 7] Gate Final de Qualidade (make pre-commit)
```

---

## 4. Phase Breakdown

### Phase 1: Dependências e Contratos das Ferramentas (Tasks 1, 2, 3)
- Adição da dependência `mcp>=1.3.0` ao `pyproject.toml`.
- Definição do protocolo `IMcpToolProvider`.
- Criação das 3 tools individuais com tipagem estrita: `KnowledgeQueryTool`, `KnowledgeListKbsTool`, `KnowledgeSearchNotesTool`.
- Criação do `KnowledgeMcpToolProvider` agregando as ferramentas do domínio `knowledge`.
- Testes unitários com mocks do `AppContainer`.

### Phase 2: Servidor SSE e Integração ao Gateway (Tasks 4, 5)
- Criação da aplicação MCP utilizando `SseServerTransport` do SDK oficial `mcp`.
- Gerenciamento de sessões para comunicação bidirecional (`GET /mcp/sse` e `POST /mcp/messages`).
- Montagem da sub-aplicação no FastAPI principal (`src/api_gateway/main.py`).
- Ajuste no `deploy/vm/Caddyfile` para permitir `/mcp/*` com buffering desativado (streaming SSE nativo).

### Phase 3: Verificação Ponta a Ponta e Gate (Tasks 6, 7)
- Suíte de testes de integração simulando o cliente MCP (handshake SSE, `initialize`, `tools/list`, `tools/call`).
- Execução do gate oficial `make pre-commit` (Ruff lint, Ruff format, Mypy strict, Pytest coverage).

---

## 5. Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Incompatibilidade de tipos Pydantic v2 no SDK MCP | Médio | Uso do SDK oficial `mcp>=1.3.0` que já é construído nativamente sobre Pydantic v2. |
| Buffering de SSE pelo proxy reverso (Caddy / Nginx) | Alto | Configuração explícita de desativação de buffer no Caddyfile (`flush_interval -1`) para rotas SSE. |
| Violação da regra Single Class per File | Alto | Cada tool, provider e transport wrapper criado em seu próprio arquivo dedicado. |
| Overhead de tokens com retornos longos do GraphRAG | Médio | Formatação concisa em Markdown na ferramenta `knowledge_query`, com opção de evidências de grafo apenas sob demanda (`include_graph_evidence=False` por padrão). |
