# Task List: Streamable HTTP/SSE MCP Server (Marco 1.22)

> **Regra de ouro:** Implement → Test → Verify (passing) → Commit.
> Cada tarefa deve ter escopo atômico, critérios de aceitação testáveis e verificação explícita.

---

## Tasks

### Task 1: Adicionar dependência oficial `mcp` ao `pyproject.toml`

**Description:** Adiciona `mcp>=1.3.0` como dependência principal do projeto no `pyproject.toml` e sincroniza o ambiente de desenvolvimento.

**Acceptance criteria:**
- [x] `pyproject.toml` contém `"mcp>=1.3.0"` em `dependencies`.
- [x] O pacote é importável em Python (`python -c "import mcp"` executa com sucesso).

**Verification:**
```bash
python -c "import mcp; print(mcp.__file__)"
```

**Files touched:**
- `pyproject.toml`

**Commit:** `chore(deps): add official mcp sdk dependency`

---

### Task 2: Implementar o protocolo `IMcpToolProvider` e as classes isoladas das Tools

**Description:** Cria o protocolo `IMcpToolProvider` e implementa as 3 classes isoladas de ferramentas no padrão Single Class per File em `src/api_gateway/mcp/tools/` e `src/api_gateway/mcp/protocols/`, além de testes unitários para cada tool.

**Acceptance criteria:**
- [x] `src/api_gateway/mcp/protocols/i_mcp_tool_provider.py` criado definindo o contrato de provedor de tools.
- [x] `src/api_gateway/mcp/tools/knowledge_query_tool.py` criado implementando `knowledge_query`.
- [x] `src/api_gateway/mcp/tools/knowledge_list_kbs_tool.py` criado implementando `knowledge_list_kbs`.
- [x] `src/api_gateway/mcp/tools/knowledge_search_notes_tool.py` criado implementando `knowledge_search_notes`.
- [x] Arquivos `__init__.py` correspondentes exportam publicamente as classes.
- [x] Testes unitários em `tests/unit/api_gateway/mcp/test_knowledge_tools.py` passando com 100% de sucesso.

**Verification:**
```bash
pytest tests/unit/api_gateway/mcp/test_knowledge_tools.py -v
mypy --strict src/api_gateway/mcp/
```

**Files touched:**
- `src/api_gateway/mcp/protocols/i_mcp_tool_provider.py`
- `src/api_gateway/mcp/protocols/__init__.py`
- `src/api_gateway/mcp/tools/knowledge_query_tool.py`
- `src/api_gateway/mcp/tools/knowledge_list_kbs_tool.py`
- `src/api_gateway/mcp/tools/knowledge_search_notes_tool.py`
- `src/api_gateway/mcp/tools/__init__.py`
- `tests/unit/api_gateway/mcp/test_knowledge_tools.py`

**Commit:** `feat(mcp): implement modular tool handlers for knowledge retrieval`

---

### Task 3: Implementar o provedor de ferramentas `KnowledgeMcpToolProvider`

**Description:** Cria o `KnowledgeMcpToolProvider` em `src/api_gateway/mcp/providers/` implementando `IMcpToolProvider`, responsável por registrar e expor as definições e schemas das ferramentas do módulo Knowledge para o servidor MCP.

**Acceptance criteria:**
- [x] `KnowledgeMcpToolProvider` herda de `IMcpToolProvider`.
- [x] Método `get_tools()` ou delegação registra as ferramentas na instância do servidor MCP.
- [x] Suporte a registro das ferramentas `knowledge_query`, `knowledge_list_kbs` e `knowledge_search_notes`.
- [x] Testes unitários em `tests/unit/api_gateway/mcp/test_knowledge_provider.py` passando.

**Verification:**
```bash
pytest tests/unit/api_gateway/mcp/test_knowledge_provider.py -v
mypy --strict src/api_gateway/mcp/providers/
```

**Files touched:**
- `src/api_gateway/mcp/providers/knowledge_mcp_tool_provider.py`
- `src/api_gateway/mcp/providers/__init__.py`
- `tests/unit/api_gateway/mcp/test_knowledge_provider.py`

**Commit:** `feat(mcp): implement knowledge mcp tool provider`

---

### Task 4: Implementar o servidor MCP com transporte SSE e gerenciamento de sessões

**Description:** Implementa a sub-aplicação Starlette/FastAPI com transporte SSE (`SseServerTransport`) do SDK `mcp`, permitindo conexões de clientes em `/sse` e troca de mensagens JSON-RPC em `/messages`.

**Acceptance criteria:**
- [x] `src/api_gateway/mcp/mcp_server_app.py` cria a aplicação com endpoints SSE e mensagens.
- [x] Handshake do MCP (`initialize`, `notifications/initialized`, `tools/list`, `tools/call`) suportado com sucesso.
- [x] Tratamento adequado de fechamento e timeout de sessões.

**Verification:**
```bash
mypy --strict src/api_gateway/mcp/
```

**Files touched:**
- `src/api_gateway/mcp/mcp_server_app.py`
- `src/api_gateway/mcp/__init__.py`

**Commit:** `feat(mcp): create streamable sse mcp server application`

---

### Task 5: Integrar a sub-aplicação MCP no FastAPI (`main.py`) e Caddyfile

**Description:** Monta a aplicação MCP no `main.py` em `/mcp` e atualiza a configuração de proxy reverso no `deploy/vm/Caddyfile` para assegurar suporte a streaming SSE (`flush_interval -1`).

**Acceptance criteria:**
- [x] Rota `/mcp` montada no FastAPI em `src/api_gateway/main.py`.
- [x] `deploy/vm/Caddyfile` configurado para rotear `/mcp/*` para o backend com buffering de resposta desativado.

**Verification:**
```bash
grep "/mcp" src/api_gateway/main.py
grep "mcp" deploy/vm/Caddyfile
```

**Files touched:**
- `src/api_gateway/main.py`
- `deploy/vm/Caddyfile`

**Commit:** `feat(mcp): mount mcp server in api gateway and configure caddy proxy`

---

### Task 6: Implementar suíte de testes de integração ponta a ponta para o MCP

**Description:** Implementa testes de integração com `httpx.AsyncClient` testando o ciclo de vida completo via transporte SSE e mensagens JSON-RPC: `initialize`, listagem de ferramentas e execução de `knowledge_list_kbs` e `knowledge_query`.

**Acceptance criteria:**
- [x] Teste de conexão SSE (`GET /mcp/sse`) recebendo evento com sessionId e URL de messages.
- [x] Teste de chamada JSON-RPC `initialize` e `tools/list`.
- [x] Teste de execução `tools/call` validando retorno formatado em Markdown.
- [x] 100% dos testes de integração passando.

**Verification:**
```bash
pytest tests/integration/test_mcp_sse_server.py -v
```

**Files touched:**
- `tests/integration/test_mcp_sse_server.py`

**Commit:** `test(mcp): add end-to-end integration tests for streamable sse mcp`

---

### Task 7: Executar validação final e gate de qualidade (`make pre-commit`)

**Description:** Executa todos os linters, formatadores, checagem estrita de tipos e suíte completa de testes para garantir conformidade com o `AGENTS.md`.

**Acceptance criteria:**
- [x] `ruff check .` com zero erros e warnings.
- [x] `ruff format --check .` 100% formatado.
- [x] `mypy --strict src/ tests/` com `No issues found`.
- [x] `make pre-commit` aprovado com sucesso.

**Verification:**
```bash
make pre-commit
```

**Files touched:**
- Todos os arquivos modificados/criados

**Commit:** `chore(mcp): complete quality gates and pre-commit checks`
