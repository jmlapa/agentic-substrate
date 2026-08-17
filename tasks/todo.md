# Task List: PydanticAI Graph Extractor, Rate Limiter (RPM/TPM) & Entity Canonicalization

## Phase 1: Rate Limiting & Concurrency Control

### Task 1: Implementar `AsyncTokenBucketLimiter`
**Description:** Criar o `AsyncTokenBucketLimiter` no `src/kernel/infrastructure/` para controle estrito de vazão baseado em janela deslizante de 60 segundos, gerenciando cotas de RPM (Requests per Minute) e TPM (Tokens per Minute) de forma assíncrona e thread-safe.

**Acceptance criteria:**
- [x] Implementa `acquire(estimated_tokens: int) -> None` com bloqueio não-bloqueante via `await asyncio.sleep(delta)`.
- [x] Mantém deques deslizantes de timestamps de requisições e contadores de tokens expirados após 60 segundos.
- [x] Suporta parâmetros configuráveis: `max_rpm: int`, `max_tpm: int`, `window_seconds: float = 60.0`.
- [x] Thread-safe e coroutine-safe utilizando `asyncio.Lock`.
- [x] 1 Classe por arquivo isolado e exportado em `src/kernel/infrastructure/__init__.py`.

**Verification:**
- [x] `uv run mypy src/kernel/infrastructure/async_token_bucket_limiter.py`

**Dependencies:** None
**Files touched:**
- `src/kernel/infrastructure/async_token_bucket_limiter.py`
- `src/kernel/infrastructure/__init__.py`
**Estimated scope:** Small (2 files)

### Task 2: Testes Unitários do `AsyncTokenBucketLimiter`
**Description:** Escrever suíte de testes unitários para o `AsyncTokenBucketLimiter` validando limitação de requisições por minuto, limitação de tokens por minuto, expiração de janela e concorrência assíncrona com múltiplas corotinas simultâneas.

**Acceptance criteria:**
- [x] Teste de RPM: 5 requisições com limite de 5 RPM são imediatas, a 6ª requisição aguarda.
- [x] Teste de TPM: requisição consumindo o teto de tokens força a próxima requisição a aguardar o término da janela.
- [x] Teste de purga: eventos antigos são descartados da memória sem vazamento.
- [x] Teste de concorrência com `asyncio.gather`.

**Verification:**
- [x] `uv run pytest tests/unit/test_async_token_bucket_limiter.py -v`

**Dependencies:** Task 1
**Files touched:**
- `tests/unit/test_async_token_bucket_limiter.py`
**Estimated scope:** Small (1 file)

---

## Checkpoint: Rate Limiting Foundation
- [x] Rate Limiter validado com 100% de cobertura nos testes unitários.

---

## Phase 2: Domain Entity Canonicalization & Registry

### Task 3: Value Object `CanonicalEntity` e Interface `IEntityRegistry`
**Description:** Modelar o Value Object `CanonicalEntity` e a interface abstrata/Protocol `IEntityRegistry` no domínio de Knowledge para padronizar e canonizar entidades ontológicas.

**Acceptance criteria:**
- [x] `CanonicalEntity` implementado como `ValueObject` (`frozen=True`) com campos: `id`, `name`, `entity_type`, `aliases: list[str]`.
- [x] `IEntityRegistry` definido como `Protocol` com métodos: `async def register_entity(kb_id: UUID, entity: CanonicalEntity) -> CanonicalEntity`, `async def get_all_distinct(kb_id: UUID) -> list[CanonicalEntity]`, `async def find_matching(kb_id: UUID, name: str, entity_type: str) -> CanonicalEntity | None`.
- [x] 1 Classe por arquivo isolado e exportado em `src/modules/knowledge/domain/value_objects/__init__.py` e `src/modules/knowledge/domain/interfaces/__init__.py`.

**Verification:**
- [x] `uv run mypy src/modules/knowledge/domain/value_objects/canonical_entity.py src/modules/knowledge/domain/interfaces/i_entity_registry.py`

**Dependencies:** None
**Files touched:**
- `src/modules/knowledge/domain/value_objects/canonical_entity.py`
- `src/modules/knowledge/domain/interfaces/i_entity_registry.py`
- `src/modules/knowledge/domain/value_objects/__init__.py`
- `src/modules/knowledge/domain/interfaces/__init__.py`
**Estimated scope:** Small (4 files)

### Task 4: Implementar `ExistingEntityRegistry` e Testes Unitários
**Description:** Implementar a classe `ExistingEntityRegistry` em `src/modules/knowledge/infrastructure/extractors/` fornecendo armazenamento assíncrono em memória com suporte a normalização de aliases e busca aproximada/exata de sinônimos.

**Acceptance criteria:**
- [x] Implementa o contrato `IEntityRegistry`.
- [x] Normaliza nomes e aliases para comparação case-insensitive sem acentuação (`stf` == `STF` == `Supremo Tribunal Federal`).
- [x] Registra novas entidades preservando atomicidade via `asyncio.Lock`.
- [x] Suíte de testes unitários validando registro, busca e correspondência de aliases.

**Verification:**
- [x] `uv run pytest tests/unit/test_existing_entity_registry.py -v`
- [x] `uv run mypy src/modules/knowledge/infrastructure/extractors/existing_entity_registry.py`

**Dependencies:** Task 3
**Files touched:**
- `src/modules/knowledge/infrastructure/extractors/existing_entity_registry.py`
- `src/modules/knowledge/infrastructure/extractors/__init__.py`
- `tests/unit/test_existing_entity_registry.py`
**Estimated scope:** Small (3 files)

---

## Checkpoint: Entity Resolution Capabilities
- [x] Registro e canonização de entidades funcionando e testados unitariamente.

---

## Phase 3: PydanticAI Agent Graph Extractor

### Task 5: Implementar `PydanticAiGraphExtractor`
**Description:** Implementar a classe `PydanticAiGraphExtractor` integrando `pydantic-ai` v2, modelo Gemini Flash-Lite, `DynamicOntologyModelBuilder`, `AsyncTokenBucketLimiter`, `ExistingEntityRegistry` e retry com Exponential Backoff + Jitter.

**Acceptance criteria:**
- [x] Implementa o protocolo `IGraphExtractor`.
- [x] Injeta o catálogo de `existing_entities` no prompt de extração para reutilização obrigatória de `id`s canônicos.
- [x] Invoca o agente `pydantic-ai` com Structured Outputs garantidos pelo Gemini Flash-Lite.
- [x] Respeita o semáforo de concorrência (`asyncio.Semaphore(max_concurrency)`) e consome tokens no rate limiter antes da chamada de rede.
- [x] Trata HTTP 429 com exponential backoff com jitter aleatório.
- [x] Suporta modo mock/fallback quando `api_key` não for fornecida (garantindo execução em ambientes de teste sem internet).

**Verification:**
- [x] `uv run pytest tests/unit/test_pydantic_ai_graph_extractor.py -v`
- [x] `uv run mypy src/modules/knowledge/infrastructure/extractors/pydantic_ai_graph_extractor.py`

**Dependencies:** Task 1, Task 4
**Files touched:**
- `src/modules/knowledge/infrastructure/extractors/pydantic_ai_graph_extractor.py`
- `src/modules/knowledge/infrastructure/extractors/__init__.py`
**Estimated scope:** Small (2 files)

### Task 6: Testes Unitários do `PydanticAiGraphExtractor`
**Description:** Criar suíte abrangente de testes unitários testando compilação dinâmica de schema, formatação de prompts com catálogo de entidades, deduplicação de nós e resiliência a 429 simulado.

**Acceptance criteria:**
- [x] Teste de extração básica com mock de LLM retornando nós e arestas válidos.
- [x] Teste de reuso de entidade existente quando o texto menciona um sinônimo cadastrado.
- [x] Teste de cadastro de nova entidade no registro após extração de conceito inédito.
- [x] Teste de resiliência com retry em caso de simulação de erro de rate limit.

**Verification:**
- [x] `uv run pytest tests/unit/test_pydantic_ai_graph_extractor.py -v`

**Dependencies:** Task 5
**Files touched:**
- `tests/unit/test_pydantic_ai_graph_extractor.py`
**Estimated scope:** Small (1 file)

---

## Checkpoint: Extractor Validation
- [x] `PydanticAiGraphExtractor` implementado e aprovado em todos os testes unitários.

---

## Phase 4: Configurações, Container IoC & Integração na Saga

### Task 7: Atualizar `AppSettings`, Container IoC e `DocumentIngestionSagaCoordinator`
**Description:** Adicionar configurações de rate limiting no `AppSettings` (`GEMINI_MAX_RPM`, `GEMINI_MAX_TPM`, `GEMINI_MAX_CONCURRENCY`), instanciar `PydanticAiGraphExtractor` no container IoC e garantir injeção de dependências correta na Saga.

**Acceptance criteria:**
- [x] `AppSettings` contém campos `gemini_max_rpm: int = 300`, `gemini_max_tpm: int = 1_000_000`, `gemini_max_concurrency: int = 15`.
- [x] `create_app_container` inicializa o `AsyncTokenBucketLimiter` e o `PydanticAiGraphExtractor` quando `gemini_api_key` estiver presente ou em modo memória.
- [x] `DocumentIngestionSagaCoordinator` repassa `kb_id` e contexto para a extração ontológica com resolução de entidades.

**Verification:**
- [x] `uv run pytest tests/unit/test_app_settings.py tests/integration/ -v`

**Dependencies:** Task 5
**Files touched:**
- `src/kernel/infrastructure/app_settings.py`
- `src/api_gateway/container.py`
- `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`
- `tests/unit/test_app_settings.py`
**Estimated scope:** Medium (4 files)

### Task 8: Testes de Integração End-to-End da Extração
**Description:** Testar o pipeline de ingestão E2E processando múltiplos Parent Chunks em paralelo com o extrator e validando a persistência no FalkorDB e no grafo.

**Acceptance criteria:**
- [x] Teste E2E executa MarkItDown ➔ Chunker ➔ Embeddings ➔ PydanticAiGraphExtractor ➔ FalkorDB.
- [x] Nós duplicados são consolidados sob o mesmo ID no FalkorDB.

**Verification:**
- [x] `uv run pytest tests/integration/test_document_ingestion_saga_coordinator.py -v`

**Dependencies:** Task 7
**Files touched:**
- `tests/integration/test_document_ingestion_saga_coordinator.py`
**Estimated scope:** Small (1 file)

---

## Checkpoint: Integration Complete
- [x] Integração E2E validada com múltiplos chunks concorrentes.

---

## Phase 5: Quality Gates & Pre-Commit

### Task 9: Execução dos Gates Oficiais de Qualidade (`make pre-commit`)
**Description:** Executar a suíte de verificação de qualidade do projeto: Ruff linter, Ruff formatador, checagem estrita de tipos no Mypy e todos os testes automatizados com medição de cobertura.

**Acceptance criteria:**
- [x] `uv run ruff check .` com zero erros.
- [x] `uv run ruff format --check .` 100% formatado.
- [x] `uv run mypy src tests` com `Success: no issues found`.
- [x] `uv run pytest --cov=src` com 100% dos testes passando.
- [x] Execução com sucesso do comando `make pre-commit`.

**Verification:**
- [x] `make pre-commit`

**Dependencies:** Task 8
**Files touched:**
- Todos os arquivos alterados
**Estimated scope:** Small

---

## Checkpoint: Final
- [x] Extrator com PydanticAI, Rate Limiter e Canonização de Entidades 100% integrado e aprovado.
