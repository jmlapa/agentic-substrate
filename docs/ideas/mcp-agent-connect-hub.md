# MCP Agent Connect Hub: Frontend Quickstart & Dynamic Tool Catalog

## Problem Statement
How might we empower developers and agent builders to frictionlessly discover, configure, and verify the Substrate MCP server across the industry's primary coding agents (Claude Code/Desktop, Cursor, GitHub Copilot, Antigravity, Gemini CLI, OpenCode, ChatGPT) directly from the web console with zero guesswork?

---

## Recommended Direction: Dynamic Agent Connect Hub (`/mcp`)

Create a dedicated first-level navigation item and view in the frontend console (`/mcp` — **Substrate MCP**) containing:
1. **Live Health & Connection Status Banner**:
   - Visual heartbeat check verifying if `/mcp/sse` is active and reachable.
   - Dynamic environment URL resolver (`http://localhost:8000/mcp/sse` in local dev vs. `https://<domain>/mcp/sse` in production/Caddy).
2. **Tabbed Client Quickstarts (Source-Grounded Configuration)**:
   - Tailored, copy-paste configurations matching the exact schema and file paths of each supported agent:
     - **Cursor** (`.cursor/mcp.json`)
     - **Claude Desktop** (`claude_desktop_config.json`)
     - **Claude Code CLI** (`claude mcp add` & `.mcp.json`)
     - **GitHub Copilot / VS Code** (`.vscode/mcp.json` with `"servers"` key)
     - **Antigravity / Antigravity CLI** (`~/.gemini/config/mcp_config.json` with `"serverUrl"`)
     - **Gemini CLI** (`~/.gemini/settings.json` & `gemini mcp add`)
     - **OpenCode** (`opencode.json` with `"type": "remote"`)
     - **ChatGPT / Custom Connectors** (Developer Mode HTTPS URL)
     - **Python & Node.js SDK** (Raw programmatic connection snippets)
3. **Dynamic Cognitive Tool Catalog**:
   - Backend-driven introspection via `GET /api/v1/mcp/info` exposing registered tools in real time.
   - For each tool (`knowledge_query`, `knowledge_list_kbs`, `knowledge_search_notes`):
     - Name, human-readable purpose, and capability tags (`GraphRAG`, `Fast-Path`, `Discovery`).
     - Interactive parameter breakdown (required vs. optional, type, and description).
     - Example tool call payload.

---

## Verified Configuration Schemas by Agent

### 1. Cursor
- **Path**: `.cursor/mcp.json` (projeto) ou `~/.cursor/mcp.json` (global)
- **UI**: Cursor Settings > Features > MCP > Add New MCP Server
- **Configuração JSON**:
```json
{
  "mcpServers": {
    "agentic-substrate": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

### 2. Claude Desktop
- **Path**:
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- **UI**: Settings > Developer > Edit Config
- **Configuração JSON**:
```json
{
  "mcpServers": {
    "agentic-substrate": {
      "type": "sse",
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

### 3. Claude Code (CLI)
- **One-Liner CLI**:
```bash
claude mcp add --transport sse agentic-substrate http://localhost:8000/mcp/sse
```
- **Path**: `.mcp.json` (projeto) ou `~/.claude.json` (global)
- **Configuração JSON**:
```json
{
  "mcpServers": {
    "agentic-substrate": {
      "type": "sse",
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```
- **Validação**: Comando `/mcp` dentro da sessão do Claude Code.

### 4. GitHub Copilot (VS Code)
- **Path**: `.vscode/mcp.json` (no root do workspace)
- **Atenção à sintaxe**: Utiliza a chave raiz `"servers"` (e não `"mcpServers"`).
- **Configuração JSON**:
```json
{
  "servers": {
    "agentic-substrate": {
      "type": "sse",
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```
- **Ativação**: No painel do Copilot Chat, selecione **Agent Mode** e valide no ícone de ferramentas (`MCP: List Servers`).

### 5. Antigravity & Antigravity CLI (AGY)
- **Path**: `~/.gemini/config/mcp_config.json` (global) ou `plugins/<nome>/mcp_config.json` (plugin)
- **Atenção à sintaxe**: Utiliza a propriedade `"serverUrl"` para conexões SSE.
- **Configuração JSON**:
```json
{
  "mcpServers": {
    "agentic-substrate": {
      "serverUrl": "http://localhost:8000/mcp/sse"
    }
  }
}
```
- **Validação**: Menu **Additional Options (...) > MCP Servers**.

### 6. Gemini CLI
- **Path**: `~/.gemini/settings.json`
- **CLI**:
```bash
gemini mcp add agentic-substrate --url http://localhost:8000/mcp/sse
```
- **Configuração JSON**:
```json
{
  "mcpServers": {
    "agentic-substrate": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

### 7. OpenCode
- **Path**: `opencode.json` / `opencode.jsonc` (projeto) ou `~/.config/opencode/opencode.json` (global)
- **CLI**:
```bash
opencode mcp add agentic-substrate --url http://localhost:8000/mcp/sse
```
- **Configuração JSON**:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "agentic-substrate": {
        "type": "remote",
        "url": "http://localhost:8000/mcp/sse",
        "enabled": true
      }
    }
  }
}
```

### 8. ChatGPT & OpenAI Codex
- **UI**: Settings > Apps / Developer Mode > Connect Custom MCP
- **URL Endpoint**: `https://<seu-dominio>/mcp/sse` (requer URL pública HTTPS em produção ou túnel em desenvolvimento).

### 9. Python SDK (`mcp`)
```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def main():
    async with sse_client("http://localhost:8000/mcp/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])


asyncio.run(main())
```

---

## Architecture & API Contract

### Novo Endpoint Backend (`src/api_gateway/routes/mcp_router.py`)
- **Rota**: `GET /api/v1/mcp/info`
- **Propósito**: Introspecção O(1) sem necessidade de conexões persistentes SSE pelo navegador.
- **Response Schema (`McpInfoDTO`)**:
```json
{
  "status": "online",
  "version": "0.8.0",
  "transport": "sse",
  "sse_endpoint": "/mcp/sse",
  "messages_endpoint": "/mcp/messages",
  "tools": [
    {
      "name": "knowledge_query",
      "description": "Consulta o grafo de conhecimento (GraphRAG)...",
      "category": "GraphRAG",
      "parameters": [
        { "name": "kb_id", "type": "string", "required": true, "description": "UUID da base" },
        { "name": "query", "type": "string", "required": true, "description": "Pergunta em linguagem natural" },
        { "name": "include_graph_evidence", "type": "boolean", "required": false, "description": "Incluir triplas do grafo" }
      ]
    },
    {
      "name": "knowledge_list_kbs",
      "description": "Lista todas as bases de conhecimento...",
      "category": "Discovery",
      "parameters": []
    },
    {
      "name": "knowledge_search_notes",
      "description": "Busca rápida por palavras-chave e cabeçalhos...",
      "category": "Fast-Path",
      "parameters": [
        { "name": "kb_id", "type": "string", "required": true, "description": "UUID da base" },
        { "name": "query", "type": "string", "required": true, "description": "Termo de busca" },
        { "name": "limit", "type": "integer", "required": false, "description": "Limite de resultados (1-50)" }
      ]
    }
  ]
}
```

---

## Key Assumptions to Validate
- [ ] O frontend consegue inferir a porta correta da API em modo de desenvolvimento (`http://localhost:8000/mcp/sse` quando o Vite roda na `3000`), enquanto em produção usa o host atual (`/mcp/sse`).
- [ ] As ferramentas expostas dinamicamente via `GET /api/v1/mcp/info` refletem fielmente qualquer nova ferramenta adicionada em `src/api_gateway/mcp/tools/` sem intervenção manual no frontend.

---

## MVP Scope
- [x] **Backend**: Endpoint REST `GET /api/v1/mcp/info` com rota e DTO tipados estritamente.
- [x] **Frontend Route & Navigation**: Nova rota `/mcp` e item no menu `Sidebar.tsx` ("Substrate MCP" com ícone de conexão).
- [x] **Client Quickstart Component**: Tabs para Cursor, Claude Desktop, Claude Code, GitHub Copilot, Antigravity, Gemini CLI, OpenCode e ChatGPT com botão de cópia de 1-clique.
- [x] **Dynamic Tools Accordion/Grid**: Listagem das ferramentas ativas com parâmetros, tipos e badges.
- [x] **Health Check Indicator**: Sinalizador visual verde/vermelho indicando disponibilidade do serviço.

---

## Not Doing (and Why)
- **Terminal Web interativo de chamadas JSON-RPC**: Desnecessário; o usuário já tem o RAG Playground (`/playground`) para testar queries e respostas.
- **Gestão de API Keys e Tokens MCP pelo Frontend**: O MCP atual no Substrate roda dentro da rede segura da VPC / máquina local sem autenticação de token bearer no MVP. Autenticação OAuth2/Bearer no MCP será tratada no marco de segurança multi-tenant.
- **Gerenciador de múltiplos servers MCP**: O Substrate opera como um servidor MCP unificado; não há múltiplos hosts a gerenciar.
