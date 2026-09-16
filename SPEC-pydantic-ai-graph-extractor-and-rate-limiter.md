# Spec: PydanticAI Graph Extractor, Rate Limiter (RPM/TPM) & Entity Canonicalization

> [!WARNING]
> **DEPRECATED / SUPERSEDED:** A extração via `PydanticAI` e o modelo Gemini Flash-Lite foram descontinuados e substituídos formalmente pela especificação [`SPEC-lean-7b-direct-openrouter-structured-extractor.md`](file:///Users/insider/personal/agentic-substrate/SPEC-lean-7b-direct-openrouter-structured-extractor.md) e pelos registros [ADR-0010](file:///Users/insider/personal/agentic-substrate/docs/decisions/0010-lean-7b-direct-openrouter-structured-extractor.md) e [ADR-0011](file:///Users/insider/personal/agentic-substrate/docs/decisions/0011-deprecation-of-pydantic-ai-legacy-parsers-and-env-hardening.md). O extrator padrão em produção é o `DirectOpenRouterGraphExtractor` (`meta-llama/llama-3.1-8b-instruct`).

## Objective
Implementar um extrator ontológico de grafos de alta performance e baixo custo (`PydanticAiGraphExtractor`) baseado em `pydantic-ai` v2 e no modelo **Gemini Flash-Lite**, acoplado a um **Rate Limiter Assíncrono com Sliding Window** (`AsyncTokenBucketLimiter`) para controle estrito de cotas (RPM e TPM) e a um mecanismo de **Resolução Cumulativa de Entidades** (`ExistingEntityRegistry`) para evitar nós duplicados no FalkorDB.

---

### User Stories & Comportamentos Esperados
1. **Extração Estruturada com PydanticAI v2:** O extrator compila dinamicamente a ontologia da Knowledge Base (`OntologySchema`) em modelos Pydantic v2 de nós e arestas e invoca o agente `pydantic-ai` com Structured Outputs garantidos pelo Gemini Flash-Lite.
2. **Controle Estrito de Vazão (RPM & TPM Limiter):** O `AsyncTokenBucketLimiter` mantém uma fila deslizante de 60 segundos com timestamps de requisições e contadores de tokens. Antes de disparar qualquer chamada à API do Gemini, o limiter verifica:
   - Requisições nos últimos 60s < `max_rpm` (ex: 300 RPM).
   - Tokens estimados nos últimos 60s + tokens do prompt atual < `max_tpm` (ex: 1.000.000 TPM).
   - Se os limites forem atingidos, a corotina aguarda com `await asyncio.sleep(tempo_restante_para_liberar_janela)`.
3. **Concorrência Assíncrona Controlada:** A execução paralela de dezenas de `ParentChunk`s é controlada por `asyncio.Semaphore(max_concurrency)` (padrão: 10 a 15 tarefas simultâneas), impedindo sobrecarga de sockets e threads.
4. **Resiliência a Erros 429 (Exponential Backoff + Full Jitter):** Caso o Google Gemini retorne HTTP 429 (`RESOURCE_EXHAUSTED`), o extrator executa retries com backoff exponencial e jitter aleatório antes de falhar.
5. **Canonização e Resolução de Entidades (Entity Canonicalization):**
   - O `ExistingEntityRegistry` armazena as entidades distintas já extraídas na KB atual (`id`, `canonical_name`, `type`, `aliases`).
   - O catálogo é injetado no system prompt de cada chunk. O modelo é instruído a reutilizar o `id` e nome canônico se a entidade for sinônimo/co-referência, criando um novo `id` normalizado apenas se for um conceito inédito.
   - Novas entidades são registradas no catálogo de forma thread-safe / async-safe.

---

## Tech Stack
- **Linguagem & Runtime:** Python 3.12+
- **Agente & Structured Outputs:** `pydantic-ai>=0.0.18` + Pydantic v2
- **Provedor de LLM:** Google Gemini via `google-genai` (`gemini-2.5-flash-lite` / `gemini-3.1-flash-lite`)
- **Controle Assíncrono:** Python `asyncio` (`asyncio.Semaphore`, `asyncio.Lock`)
- **Qualidade & Tipagem:** Ruff (linter/formatter), Mypy (`strict = true`), Pytest com `pytest-asyncio`

---

## Commands
```bash
# Executar suíte completa de testes unitários do extrator e rate limiter
uv run pytest tests/unit/test_pydantic_ai_graph_extractor.py tests/unit/test_async_token_bucket_limiter.py -v

# Checagem estrita de tipos
uv run mypy src/modules/knowledge/infrastructure/extractors/ src/kernel/infrastructure/

# Linter e formatação
uv run ruff check src/modules/knowledge/infrastructure/extractors/
uv run ruff format --check src/modules/knowledge/infrastructure/extractors/

# Gate oficial
make pre-commit
```

---

## Project Structure (Single Class per File)
```
src/
├── kernel/
│   └── infrastructure/
│       ├── async_token_bucket_limiter.py          # Rate limiter genérico por RPM e TPM com sliding window
│       ├── rate_limited_async_transport.py        # Transporte HTTPX assíncrono com rate limiting e retry 429
│       └── __init__.py
└── modules/
    └── knowledge/
        ├── domain/
        │   ├── interfaces/
        │   │   ├── i_graph_extractor.py           # Protocol de extração ontológica assíncrona
        │   │   └── i_entity_registry.py           # Protocol para registro e consulta de entidades conhecidas
        │   └── value_objects/
        │       ├── canonical_entity.py            # VO representando entidade canônica (id, type, name, aliases)
        │       └── extracted_graph.py             # VO agrupando nós e arestas extraídas
        └── infrastructure/
            └── extractors/
                ├── existing_entity_registry.py    # Implementação em memória do catálogo cumulativo
                ├── dynamic_ontology_model_builder.py # Construtor de classes Pydantic v2 dinâmicas
                ├── pydantic_ai_graph_extractor.py # Adaptador de produção com PydanticAI + Rate Limiter
                └── __init__.py                    # Facade exportadora
```

---

## Code Style & Architecture Conventions

### 1. Sliding Window Token & Request Limiter
```python
# src/kernel/infrastructure/async_token_bucket_limiter.py
import asyncio
import time
from collections import deque


class AsyncTokenBucketLimiter:
    def __init__(
        self, max_rpm: int = 300, max_tpm: int = 1_000_000, window_seconds: float = 60.0
    ) -> None:
        self._max_rpm = max_rpm
        self._max_tpm = max_tpm
        self._window = window_seconds
        self._requests: deque[float] = deque()
        self._token_events: deque[tuple[float, int]] = deque()
        self._current_tokens: int = 0
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                while self._requests and now - self._requests[0] >= self._window:
                    self._requests.popleft()
                while self._token_events and now - self._token_events[0][0] >= self._window:
                    _, old_tokens = self._token_events.popleft()
                    self._current_tokens -= old_tokens

                if (
                    len(self._requests) < self._max_rpm
                    and self._current_tokens + estimated_tokens <= self._max_tpm
                ):
                    self._requests.append(now)
                    self._token_events.append((now, estimated_tokens))
                    self._current_tokens += estimated_tokens
                    return

                oldest_req = self._requests[0] if self._requests else now
                oldest_tok = self._token_events[0][0] if self._token_events else now
                sleep_time = max(
                    0.05, min(oldest_req + self._window - now, oldest_tok + self._window - now)
                )
                await asyncio.sleep(sleep_time)
```

### 2. Transporte HTTPX Customizado com Rate Limiting
```python
# src/kernel/infrastructure/rate_limited_async_transport.py
import httpx
from src.kernel.infrastructure.async_token_bucket_limiter import AsyncTokenBucketLimiter


class RateLimitedAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        rate_limiter: AsyncTokenBucketLimiter,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._limiter = rate_limiter
        self._transport = transport or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        estimated_tokens = max(1, len(request.content) // 4) if request.content else 100
        await self._limiter.acquire(estimated_tokens)
        return await self._transport.handle_async_request(request)
```

### 3. Extrator com PydanticAI e Resolução de Entidades
```python
# Trecho de execução no pydantic_ai_graph_extractor.py
class PydanticAiGraphExtractor(IGraphExtractor):
    def __init__(
        self,
        rate_limiter: AsyncTokenBucketLimiter,
        entity_registry: IEntityRegistry | None = None,
        model_name: str = "gemini-2.5-flash-lite",
        api_key: str | None = None,
    ) -> None:
        self._limiter = rate_limiter
        self._registry = entity_registry or ExistingEntityRegistry()
        self._model_name = model_name
        self._api_key = api_key
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._model_name = model_name

    async def extract_graph(
        self,
        markdown_text: str,
        ontology: OntologySchema,
    ) -> ExtractedGraph:
        async with self._semaphore:
            estimated_tokens = len(markdown_text) // 4 + 500
            await self._limiter.acquire(estimated_tokens)
            
            existing = await self._registry.get_all_distinct()
            # Executa agente PydanticAI com schema dinâmico e lista de entidades existentes
            # ...
```

---

## Testing Strategy
- **`tests/unit/test_async_token_bucket_limiter.py`**:
  - Testar restrição de RPM (disparar 10 requisições com limite de 5 RPM e medir tempo total >= 60s).
  - Testar restrição de TPM (disparar requisição pesada que esgota tokens e validar enfileiramento).
  - Testar limpeza automática de eventos expirados da janela deslizante.
- **`tests/unit/test_pydantic_ai_graph_extractor.py`**:
  - Testar compilação de modelos dinâmicos com `PydanticAI`.
  - Testar injeção e reuso de `canonical_id` quando entidade já existe no catálogo.
  - Testar resiliência com mock de erro 429 e retry bem-sucedido.
- **`tests/integration/test_pydantic_ai_e2e_extraction.py`**:
  - Testar extração real em lote com 20 chunks concorrentes respeitando cotas sem travar o event loop.

---

## Boundaries
- **Always:**
  - Manter 1 classe por arquivo em todas as camadas.
  - Tipagem 100% estrita sem `# type: ignore` desnecessário.
  - Respeitar estritamente o `acquire()` de RPM/TPM antes de qualquer chamada HTTP para LLM.
- **Ask first:**
  - Alteração de limites padrão de RPM/TPM nas configurações da aplicação (`AppSettings`).
  - Mudança do modelo padrão para modelos de custo superior (ex: Gemini Pro).
- **Never:**
  - Realizar chamadas síncronas bloqueantes dentro do event loop do asyncio.
  - Criar novos nós de entidades no grafo para conceitos que já possuem ID canônico registrado no catálogo.

---

## Success Criteria
- [ ] O `AsyncTokenBucketLimiter` impede violações de RPM e TPM sob alta concorrência assíncrona.
- [ ] O `PydanticAiGraphExtractor` extrai nós e arestas válidos conforme o `OntologySchema` fornecido.
- [ ] O catálogo cumulativo `ExistingEntityRegistry` deduplica sinônimos e mantém coerência entre chunks.
- [ ] Suíte de testes unitários e de integração com 100% de aprovação e cobertura >= 95%.
- [ ] Gate oficial `make pre-commit` aprovado com zero erros no Ruff e Mypy Strict.
