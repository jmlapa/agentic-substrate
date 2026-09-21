# Spec: MCP Agent Connect Hub (Marco 1.24)

| Status | Versão | Autor | Módulos Afetados | Data |
|---|---|---|---|---|
| **Implemented** | `v0.9.0` | AI Pair & Human Engineer | `api-gateway`, `frontend-console` | 2026-09-21 |

---

## 1. Objective

Disponibilizar no console web (`/frontend`) uma central de conexões rápida, intuitiva e auto-explicativa (**MCP Agent Connect Hub** em `/mcp`), permitindo que desenvolvedores e operadores de agentes autônomos descubram, configurem e validem a integração do servidor MCP do **Agentic Substrate** com os principais coding agents e plataformas de IA do mercado:
- **Claude Desktop**
- **Claude Code (CLI)**
- **Cursor**
- **GitHub Copilot (VS Code Agent Mode)**
- **Antigravity / Antigravity CLI (Google DeepMind)**
- **Gemini CLI**
- **OpenCode**
- **ChatGPT / OpenAI Codex (Custom Connectors)**
- **Python & Node.js SDKs**

A interface deve prover:
1. **Verificação de Saúde (Health Check & Heartbeat):** Indicativo visual em tempo real de status (`Online` / `Offline`) e latência do servidor MCP.
2. **Guias Práticos com 1-Click Copy:** Schemas JSON e comandos CLI estritamente fiéis às documentações oficiais de cada ferramenta, com resolução dinâmica da URL do ambiente (`http://localhost:8000/mcp/sse` em desenvolvimento local e `https://<domain>/mcp/sse` em produção).
3. **Catálogo Dinâmico de Ferramentas Cognitivas:** Exibição em tempo real das tools registradas no servidor (`knowledge_query`, `knowledge_list_kbs`, `knowledge_search_notes`), detalhando descrições, parâmetros exigidos/opcionais, tipos e exemplos de payload via endpoint REST de introspecção `GET /api/v1/mcp/info`.

---

### User Stories

1. **Desenvolvedor no Cursor:** O usuário acessa `/mcp`, clica na aba "Cursor", copia o snippet JSON pré-formatado com 1 clique e cola no seu `.cursor/mcp.json`. Em seguida, seu Cursor já enxerga as tools do Substrate.
2. **Desenvolvedor no Claude Code:** O usuário clica na aba "Claude Code", copia o comando `claude mcp add --transport sse agentic-substrate <url>` e executa no terminal.
3. **Engenheiro no GitHub Copilot:** O usuário visualiza o aviso de schema específico do VS Code (`"servers"` em vez de `"mcpServers"`) e copia o bloco exato para `.vscode/mcp.json`.
4. **Operador Antigravity / Gemini CLI:** O usuário obtém a sintaxe exata com `"serverUrl"` para o `~/.gemini/config/mcp_config.json` sem cometer erros de digitação.
5. **Explorador de Ferramentas:** O usuário inspeciona o catálogo dinâmico de ferramentas para entender quais argumentos cada tool exige (ex: `kb_id`, `query`, `include_graph_evidence`) e o que esperar de resposta.

---

## 2. Tech Stack

### Backend (`src/api_gateway/`)
- **Linguagem & Runtime:** Python 3.12+ (compatível com 3.13)
- **Framework Web:** FastAPI `>=0.115.0`, Starlette `>=0.38.0`
- **MCP SDK:** `mcp >= 1.3.0` (MCPServer, SSE transport)
- **Tipagem & Validação:** Pydantic v2 (`pydantic.BaseModel`) com Mypy em modo estrito (`strict = true`)

### Frontend (`frontend/`)
- **Linguagem & Runtime:** TypeScript 5.5+, React 18.3.1
- **Build Tool:** Vite 5.4+
- **Estilização:** Tailwind CSS 3.4+ com Dark Theme nativo do Substrate (Zinc/Indigo/Emerald)
- **Ícones:** Lucide React (`Terminal`, `Copy`, `Check`, `Activity`, `Cpu`, `Layers`, `ExternalLink`, etc.)
- **Gerenciamento de Estado & Requisições:** TanStack React Query v5 (polling de status a cada 10s e cache de introspecção) + Axios

---

## 3. Commands

```bash
# Backend - Linting & Tipagem Estrita
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy --strict src/api_gateway/

# Backend - Testes Unitários e de Integração
uv run pytest tests/unit/api_gateway/test_mcp_controller.py -v
uv run pytest tests/integration/test_mcp_sse_server.py -v

# Frontend - Instalação, Lint, Typecheck e Build
cd frontend && npm install
npm run lint
npm run build

# Gate Completo Pré-Commit (AGENTS.md)
make pre-commit
```

---

## 4. Project Structure

### Backend Additions
```
src/api_gateway/
├── controllers/
│   └── mcp_controller.py          # GET /api/v1/mcp/info endpoint
├── dtos/
│   ├── mcp_tool_parameter_dto.py  # DTO para metadados de parâmetros
│   ├── mcp_tool_info_dto.py       # DTO para cada ferramenta exposta
│   └── mcp_info_response_dto.py   # DTO resposta da introspecção
└── main.py                        # Inclusão do mcp_controller no router
```

### Frontend Additions & Modifications
```
frontend/
├── vite.config.ts                 # Proxy para /mcp -> http://localhost:8000
└── src/
    ├── api/
    │   └── mcp-api.ts             # Cliente Axios e tipagens da API MCP Info
    ├── utils/
    │   └── mcpAuth.ts             # Utilitários de encoding e headers Basic Auth (RFC 7617)
    ├── hooks/
    │   └── useMcpInfo.ts          # TanStack Query hook com polling de saúde
    ├── components/
    │   └── layout/
    │       └── Sidebar.tsx        # Inclusão de item de navegação "Substrate MCP"
    ├── pages/
    │   └── mcp/
    │       ├── McpConnectHubPage.tsx        # View principal do Hub
    │       ├── components/
    │       │   ├── McpHealthBanner.tsx      # Card de status online/latência/URL
    │       │   ├── McpBasicAuthPanel.tsx    # Card interativo de credenciais Caddy Basic Auth
    │       │   ├── McpClientSelectorTabs.tsx# Abas por agente com injeção dinâmica de headers
    │       │   ├── McpToolsCatalog.tsx      # Accordion/grid das tools ativas
    │       │   └── McpCodeSnippet.tsx       # Bloco de código com highlight e copy
    └── App.tsx                    # Rota /mcp -> McpConnectHubPage

```

---

## 5. Code Style & Architecture

### Backend: Single Class per File & Strict Typing
Cada DTO e controller possui seu próprio arquivo dedicado, com tipagem 100% explícita.

```python
# src/api_gateway/dtos/mcp_tool_parameter_dto.py
from pydantic import BaseModel, ConfigDict


class McpToolParameterDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    type: str
    required: bool
    description: str
```

```python
# src/api_gateway/controllers/mcp_controller.py
from fastapi import APIRouter, Request
from src.api_gateway.dtos.mcp_info_response_dto import McpInfoResponseDTO

router = APIRouter(prefix="/api/v1/mcp", tags=["Model Context Protocol"])


@router.get("/info", response_model=McpInfoResponseDTO)
async def get_mcp_info(request: Request) -> McpInfoResponseDTO:
    # Introspecção direta do catálogo de ferramentas ativas
    ...
```

### Frontend: Clean React 18 Functional Components & Accessibility
Uso de Tailwind CSS com feedback de cópia instantâneo (`copied` state de 2 segundos) e tratamento gracioso de offline/loading.

```tsx
// Exemplo de componente de snippet de código com copy
export const McpCodeSnippet: React.FC<{ code: string; language?: string; title?: string }> = ({
  code,
  language = 'json',
  title,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 overflow-hidden font-mono text-xs">
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800/80 bg-zinc-900/50">
        <span className="text-zinc-400 text-[11px]">{title || language}</span>
        <button onClick={handleCopy} className="text-zinc-400 hover:text-zinc-100 flex items-center gap-1.5">
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span className="text-[11px]">{copied ? 'Copiado!' : 'Copiar'}</span>
        </button>
      </div>
      <pre className="p-4 text-zinc-300 overflow-x-auto">{code}</pre>
    </div>
  );
};
```

---

## 6. Configurações Homologadas por Agente (Matriz de Sintaxe)

| Agente | Arquivo / Destino | Sintaxe & Particularidades Oficiais |
|---|---|---|
| **Cursor** | `.cursor/mcp.json` (projeto) ou `~/.cursor/mcp.json` | Chave raiz `"mcpServers"`, propriedade `"url": "<sse_url>"` |
| **Claude Desktop** | `claude_desktop_config.json` | Chave raiz `"mcpServers"`, propriedades `"type": "sse"`, `"url": "<sse_url>"` |
| **Claude Code (CLI)** | `.mcp.json` ou comando CLI | `claude mcp add --transport sse agentic-substrate <sse_url>` |
| **GitHub Copilot** | `.vscode/mcp.json` | **Chave raiz `"servers"`** (e não `mcpServers`), propriedades `"type": "sse"`, `"url": "<sse_url>"` |
| **Antigravity CLI** | `~/.gemini/config/mcp_config.json` | **Propriedade `"serverUrl"`** (e não `url`): `"mcpServers": { "agentic-substrate": { "serverUrl": "<sse_url>" } }` |
| **Gemini CLI** | `~/.gemini/settings.json` ou CLI | `gemini mcp add agentic-substrate --url <sse_url>` ou bloco `"mcpServers"` |
| **OpenCode** | `opencode.json` | **Chave `"mcp": { "servers": { "agentic-substrate": { "type": "remote", "url": "<sse_url>", "enabled": true } } }`** |
| **ChatGPT / Custom** | Settings > Developer Mode > Custom MCP | URL pública HTTPS (`https://<domain>/mcp/sse`) |
| **Python SDK** | Script Python | `from mcp.client.sse import sse_client` + `ClientSession` |
| **Node.js SDK** | Script Node/TS | `import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js"` |

---

## 7. Testing Strategy

1. **Backend Unit Tests (`tests/unit/api_gateway/test_mcp_controller.py`):**
   - Testar endpoint `GET /api/v1/mcp/info` com mock do container/FastAPI app.
   - Validar se status retorna `"online"`, `transport` é `"sse"`, e lista de tools contém `knowledge_query`, `knowledge_list_kbs` e `knowledge_search_notes` com parâmetros completos.
2. **Backend Integration Tests:**
   - Testar chamada HTTP via `httpx.AsyncClient` contra a aplicação FastAPI montada.
3. **Frontend Build & Types Validation:**
   - Executar `npm run build` garantindo zero erros de tipagem TypeScript no React.
   - Testar renderização de cada aba de agente garantindo que todos os snippets JSON são válidos (`JSON.parse` executa sem erro).
4. **Pre-Commit Quality Gate:**
   - Executar `make pre-commit` garantindo 100% de conformidade com `AGENTS.md`.

---

## 8. Boundaries

- **Always:**
  - Seguir a regra inegociável de **Single Class per File** para todos os novos DTOs e controllers no backend.
  - Usar tipagem estrita no TypeScript (sem `any`) e Mypy estrito no Python.
  - Computar a URL do SSE de forma inteligente (respeitando `window.location.origin` e portas de dev `8000`).
- **Ask First:**
  - Alterar o protocolo base do MCP (`/mcp/sse`) ou dependências core.
- **Never:**
  - Embutir dependências pesadas de clientes SSE no navegador para o health check básico.
  - Utilizar mono-arquivos no backend.
  - Quebrar compatibilidade com endpoints existentes da API REST.

---

## 9. Success Criteria

- [ ] Endpoint `GET /api/v1/mcp/info` implementado e retornando catálogo dinâmico de tools com status online.
- [ ] Rota `/mcp` adicionada na Sidebar e no roteador do Frontend.
- [ ] Indicador visual de saúde (Online/Offline) responsivo no topo da página.
- [ ] 10 abas de clientes implementadas com snippets validados e botão de cópia rápida funcional.
- [ ] Catálogo de ferramentas renderizado dinamicamente com nomes, descrições, parâmetros e badges.
- [ ] 100% de aprovação no `make pre-commit` (Ruff, Mypy strict, Pytest) e `npm run build`.

---

## 10. Open Questions & Resolutions

- **Q: O health check no frontend deve fazer uma requisição SSE real ou REST?**
  - **Resolução:** Utilizará o endpoint REST `GET /api/v1/mcp/info`. Isso evita conexões SSE infinitas no navegador que consumiriam conexões do pool HTTP, garantindo latência imediata e compatibilidade total.
- **Q: Como o usuário diferencia ambiente local (localhost:8000) de produção (meudominio.com)?**
  - **Resolução:** O frontend detecta se `window.location.hostname` é `localhost` ou `127.0.0.1`. Se for, monta `http://localhost:8000/mcp/sse` (porta padrão da API). Se estiver em produção, monta `${window.location.origin}/mcp/sse`. Além disso, um campo editável ou seletor rápido permite ao usuário customizar a URL base se estiver usando túnel ngrok ou portas alternativas.
- **Q: Como tratar a autenticação quando o Caddy está com a regra `rules/auth.caddy` (Basic Auth) ativa na VM?**
  - **Resolução:** O hub disponibiliza o componente `McpBasicAuthPanel` com toggle reativo. Ao informar usuário e senha, o cabeçalho HTTP padrão `Authorization: Basic <base64>` (RFC 7617) é gerado e injetado automaticamente na chave `"headers"` de todos os 10 clientes MCP.
  - **Decisão de Segurança:** Credenciais embutidas na URL (`https://user:pass@host/mcp/sse`) foram expressamente descartadas por serem depreciadas pela RFC 3986 (seção 3.2.1) e causarem vazamento de senhas em logs de acesso, histórico e cabeçalhos Referer, além de serem descartadas por clientes SSE modernos. O Caddy valida o cabeçalho `Authorization`, tornando a abordagem baseada em headers 100% interoperável e segura.

