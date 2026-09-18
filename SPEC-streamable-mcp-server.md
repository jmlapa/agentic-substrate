# SPEC-streamable-mcp-server: Streamable HTTP/SSE MCP Server

| Status | Versão | Autor | Módulos Afetados | Data |
|---|---|---|---|---|
| **Implemented** | `v0.8.0` | AI Pair & Human Engineer | `api-gateway`, `knowledge`, `kernel` | 2026-09-18 |

---

## 1. Objective

Expor as capacidades cognitivas e de recuperação do **Agentic Substrate** para agentes autônomos externos (ex: Claude Desktop, Cursor, LangGraph, CrewAI, AutoGen, AutoGPT) via **Model Context Protocol (MCP)** sobre **HTTP com Server-Sent Events (SSE)**.

A interface MCP atuará como um servidor unificado na borda do sistema (`api-gateway`), permitindo que agentes remotos descubram ferramentas (`tools/list`), executem consultas estruturadas de GraphRAG (`tools/call`) e realizem buscas rápidas em bases de conhecimento sem complexidade acidental de múltiplos sockets ou SDKs proprietários.

### User Stories & Cenários
1. **Agente Pesquisador:** Um agente autônomo conecta-se via SSE a `/mcp/sse`, lista ferramentas e invoca `knowledge_query` para responder perguntas complexas com embasamento factual em grafos e síntese do Gemma 4.
2. **Agente de Busca Rápida (Fast Path):** Um agente precisa localizar notas ou documentos específicos dentro de uma base antes de aprofundar a navegação, utilizando `knowledge_search_notes` para busca semântica/léxica instantânea sem gastar tokens com síntese de LLM.
3. **Agente Orquestrador / Roteador:** Um supervisor multi-agente invoca `knowledge_list_kbs` para descobrir quais bases existem no Substrate e rotear as tarefas de pesquisa para a base mais relevante.

---

## 2. Tech Stack & Dependências

- **Runtime:** Python `>=3.11` (executando em 3.12).
- **Core Framework:** `FastAPI >= 0.115.0`, `Starlette >= 0.38.0`.
- **MCP Protocol SDK:** `mcp >= 1.3.0` (SDK oficial da Anthropic para Python com suporte a `SseServerTransport` e Pydantic v2).
- **Async Concurrency:** `asyncio`, `anyio`, `uvicorn[standard]` com `uvloop`.
- **Data Validation:** `pydantic >= 2.8.0`.

---

## 3. Comandos de Verificação e Gates

```bash
# Instalação / Sincronização de dependências
uv pip install -e ".[dev]"

# Linting e Formatação (Zero Erros)
ruff check src/ tests/
ruff format --check src/ tests/

# Checagem de Tipagem Estrita (Zero Any implícito)
mypy --strict src/ tests/

# Execução de Testes Unitários e de Integração
pytest tests/unit/api_gateway/mcp/ -v --cov=src/api_gateway/mcp/
pytest tests/integration/api_gateway/mcp/ -v

# Gate Completo Pré-Commit (Conforme AGENTS.md)
make pre-commit
```

---

## 4. Arquitetura e Estrutura de Projeto (Single Class per File)

Seguindo estritamente o `AGENTS.md` (Single Class / DTO / Interface per File), a implementação do MCP é organizada de forma modular e desacoplada:

```
src/
├── api_gateway/
│   ├── mcp/
│   │   ├── __init__.py                          # Facade exportadora do MCP
│   │   ├── mcp_server_app.py                    # Configuração da sub-aplicação Starlette/FastAPI com SseServerTransport
│   │   ├── mcp_session_manager.py               # Gerenciador de sessões e rotas SSE /messages
│   │   ├── protocols/
│   │   │   ├── __init__.py
│   │   │   └── i_mcp_tool_provider.py           # Protocolo base para provedores de tools por módulo
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   └── knowledge_mcp_tool_provider.py   # Registrador das tools do módulo knowledge
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── knowledge_query_tool.py          # Handler isolado para knowledge_query
│   │       ├── knowledge_list_kbs_tool.py       # Handler isolado para knowledge_list_kbs
│   │       └── knowledge_search_notes_tool.py   # Handler isolado para knowledge_search_notes
```

---

## 5. Contratos das Tools do MVP (Foco em Retrieval & Descoberta)

### 1. `knowledge_query`
- **Descrição:** Realiza consulta híbrida GraphRAG sobre uma Base de Conhecimento, combinando busca vetorial, travessia ontológica em FalkorDB e síntese factual densa (Gemma 4) com citações de fontes.
- **Input Schema:**
  - `kb_id` (str): UUID da Base de Conhecimento.
  - `query` (str): Pergunta ou instrução de pesquisa em linguagem natural.
  - `include_graph_evidence` (bool, default `False`): Se `True`, anexa as evidências do subgrafo e entidades canônicas no final da resposta.
- **Output:** Texto em Markdown estruturado contendo a resposta sintetizada e referências documentais.

### 2. `knowledge_list_kbs`
- **Descrição:** Lista as Bases de Conhecimento disponíveis no Agentic Substrate com contagem de documentos, descrição e status.
- **Input Schema:** Vazio (sem parâmetros obrigatórios).
- **Output:** Lista estruturada em Markdown ou JSON com `id`, `name`, `description`, `total_documents` e `status`.

### 3. `knowledge_search_notes`
- **Descrição:** Busca rápida por termos e tópicos em notas e documentos de uma Base de Conhecimento (fast-path sem síntese de LLM), retornando títulos, caminhos e trechos relevantes.
- **Input Schema:**
  - `kb_id` (str): UUID da Base de Conhecimento.
  - `query` (str): Termo ou prefixo de busca.
  - `limit` (int, default `10`): Quantidade máxima de resultados (1 a 50).
- **Output:** Lista em Markdown contendo os documentos correspondentes, links de referência e previews textuais.

---

## 6. Code Style & Exemplo de Implementação

Seguindo o padrão de injeção de dependências e tipagem estrita do repositório:

```python
# src/api_gateway/mcp/tools/knowledge_query_tool.py
from dataclasses import dataclass
from uuid import UUID

from mcp.types import TextContent

from src.api_gateway.container import AppContainer
from src.kernel.domain.result import Err
from src.modules.knowledge.application.use_cases.query_knowledge import (
    QueryKnowledgeRequest,
)


@dataclass(frozen=True)
class KnowledgeQueryTool:
    container: AppContainer

    @property
    def name(self) -> str:
        return "knowledge_query"

    @property
    def description(self) -> str:
        return (
            "Consulta o grafo de conhecimento (GraphRAG) para responder perguntas complexas "
            "com síntese fact-dense e citações de fontes documentais."
        )

    async def execute(
        self,
        kb_id: str,
        query: str,
        include_graph_evidence: bool = False,
    ) -> list[TextContent]:
        try:
            parsed_kb_id = UUID(kb_id)
        except ValueError:
            return [
                TextContent(type="text", text=f"Erro: kb_id inválido: '{kb_id}'. Deve ser um UUID.")
            ]

        use_case = self.container.query_knowledge_use_case
        request = QueryKnowledgeRequest(
            kb_id=parsed_kb_id,
            query=query,
            include_subgraph=include_graph_evidence,
        )
        res = await use_case.execute(request)
        if isinstance(res, Err):
            return [TextContent(type="text", text=f"Erro ao consultar KB: {res.error.message}")]

        return [TextContent(type="text", text=res.value.answer)]
```

---

## 7. Testing Strategy

1. **Testes Unitários de Tools (`tests/unit/api_gateway/mcp/`):**
   - Mock do `AppContainer` e dos casos de uso (`QueryKnowledgeUseCase`, `ListKnowledgeBasesUseCase`, `QuickSearchNotesUseCase`).
   - Validação de conversão de tipos (ex: string UUID para `UUID`), validação de limites e sanitização.
   - Verificação do tratamento de erros com mapeamento claro para respostas em texto amigáveis ao agente.

2. **Testes de Integração do Protocolo MCP (`tests/integration/api_gateway/mcp/`):**
   - Uso de `httpx.AsyncClient` com transporte ASGI contra o FastAPI.
   - Handshake do protocolo MCP via SSE:
     - `GET /mcp/sse` -> recebe evento `endpoint` com a URL do canal de mensagens.
     - `POST /mcp/messages?session_id=...` com `initialize` -> valida resposta JSON-RPC 2.0.
     - `POST /mcp/messages?session_id=...` com `tools/list` -> valida lista e schemas das 3 ferramentas.
     - `POST /mcp/messages?session_id=...` com `tools/call` -> valida chamada e retorno de `knowledge_query`, `knowledge_list_kbs` e `knowledge_search_notes`.

---

## 8. Boundaries (Limites e Regras Inegociáveis)

### Always Do
- **Single Class per File:** Cada tool, provider, protocolo e wrapper deve residir em seu próprio arquivo.
- **In-Process Direct Call:** O MCP deve invocar os Use Cases diretamente através do `AppContainer`, sem hops de rede adicionais.
- **Limpeza de Context Window:** Outputs de tools para LLMs devem priorizar síntese legível em Markdown, evitando despejar JSONs desnecessários.
- **Strict Typing:** Mypy em modo `strict = true`, tipagem explícita de todos os argumentos e retornos.

### Not Doing (Escopo Excluído do MVP)
- **Ingestão Multimodal via MCP:** Não implementada neste momento. Arquivos binários pesados (PDFs, imagens) e uploads continuam sendo processados via API REST multipart/form-data (`/api/v1/knowledge/bases/{id}/documents`).
- **Operações Destrutivas:** Nenhuma tool para deletar KBs, documentos ou ontologias será exposta no MCP para prevenir acidentes por agentes autônomos.
- **WebSockets:** O transporte é estritamente HTTP + SSE (Server-Sent Events) conforme especificação oficial do MCP.

### Never Do
- Jamais criar um mono-arquivo agrupando múltiplas classes de tools ou schemas.
- Jamais invocar endpoints HTTP REST do próprio gateway a partir do MCP (evitar "a armadilha do proxy").
- Jamais silenciar erros com `except Exception: pass`.

---

## 9. Success Criteria

- [ ] Dependência oficial `mcp` adicionada ao `pyproject.toml` (`mcp>=1.3.0`).
- [ ] Sub-aplicação MCP montada no FastAPI servindo rotas `/mcp/sse` e `/mcp/messages`.
- [ ] 3 ferramentas de recuperação e descoberta (`knowledge_query`, `knowledge_list_kbs`, `knowledge_search_notes`) registradas e expostas via `tools/list`.
- [ ] Testes unitários para todas as tools com cobertura e isolamento de dependências.
- [ ] Testes de integração cobrindo o handshake SSE, `initialize`, `tools/list` e `tools/call`.
- [ ] Aprovação completa no gate `make pre-commit` (Ruff lint/format, Mypy estrito, Pytest).
