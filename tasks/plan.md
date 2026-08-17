# Implementation Plan: PydanticAI Graph Extractor, Rate Limiter (RPM/TPM) & Entity Canonicalization

## Overview
Implementar o extrator ontológico de grafos de alta performance e baixo custo (`PydanticAiGraphExtractor`) baseado em `pydantic-ai` v2 e no modelo **Gemini Flash-Lite** (`gemini-2.5-flash-lite` / `gemini-3.1-flash-lite`), integrado a um **Rate Limiter Assíncrono com Sliding Window** (`AsyncTokenBucketLimiter`) para controle estrito de RPM (Requests por Minuto) e TPM (Tokens por Minuto), e a um catálogo cumulativo de **Canonização de Entidades** (`ExistingEntityRegistry`) que impede a criação de nós duplicados no FalkorDB.

---

## Architecture Decisions

1. **Controle de Vazão Universal com Sliding Window (`AsyncTokenBucketLimiter`)**:
   - Manter histórico deslizante de 60 segundos de requisições e tokens estimados (`len(text) // 4 + overhead_prompt`).
   - Bloquear corotinas de forma não-bloqueante (`await asyncio.sleep(delta)`) quando `current_rpm >= max_rpm` ou `current_tpm >= max_tpm`.
   - Localização no `kernel/infrastructure/` para que outros agentes e serviços possam reutilizar a mesma disciplina de rate limiting.

2. **Resolução e Canonização de Entidades (`ExistingEntityRegistry`)**:
   - `CanonicalEntity`: Value Object contendo `id` normalizado, `name`, `type` e lista de `aliases` conhecidos.
   - `IEntityRegistry`: Protocolo de domínio para registro e consulta de entidades conhecidas por Knowledge Base.
   - `ExistingEntityRegistry`: Implementação thread-safe / async-safe (com `asyncio.Lock`) que armazena entidades em memória e pode ser pré-populada a partir do grafo FalkorDB.
   - Injeção dinâmica no System Prompt do PydanticAI para reutilização obrigatória de `id`s canônicos quando houver equivalência semântica.

3. **Extração Ontológica Estruturada com PydanticAI v2**:
   - Compilação dos modelos dinâmicos de nós e arestas a partir do `OntologySchema` da KB.
   - Execução do agente `pydantic-ai` solicitando `result_type=ExtractedGraphModel` diretamente ao Gemini Flash-Lite.
   - Resiliência com Exponential Backoff + Full Jitter para capturar eventuais respostas 429 da API do Google.

4. **Concorrência Assíncrona Controlada**:
   - Pool de concorrência com `asyncio.Semaphore(max_concurrency)` (padrão: 10 a 15 tarefas simultâneas) para processar os `ParentChunk`s de forma paralela sem sobrecarregar conexões HTTP ou o event loop.

5. **Aderência Rigorosa ao `AGENTS.md`**:
   - 1 Classe / 1 Interface / 1 DTO por arquivo isolado.
   - Mypy em modo estrito (`strict = true`) sem nenhum `Any` implícito.
   - Facades em `__init__.py` atuando unicamente como re-exportadores.

---

## Task List

### Phase 1: Rate Limiting & Concurrency Control
- [ ] **Task 1: Implementar `AsyncTokenBucketLimiter`**
  - Sliding window de 60s para RPM e TPM com lock assíncrono.
- [ ] **Task 2: Testes Unitários Abrangentes do `AsyncTokenBucketLimiter`**
  - Validar limites de RPM, limites de TPM, expiração da janela e concorrência.

### Checkpoint: Rate Limiting Foundation
- [ ] Rate Limiter validado com 100% de cobertura e zero erros de concorrência.

### Phase 2: Domain Entity Canonicalization & Registry
- [ ] **Task 3: Value Object `CanonicalEntity` e Interface `IEntityRegistry`**
  - Modelar entidade canônica e contrato do catálogo no domínio.
- [ ] **Task 4: Implementar `ExistingEntityRegistry` e Testes Unitários**
  - Implementação thread-safe com busca, registro e deduplicação de sinônimos.

### Checkpoint: Entity Resolution Capabilities
- [ ] Modelos de canonização e catálogo testados e exportados nas facades.

### Phase 3: PydanticAI Agent Graph Extractor
- [ ] **Task 5: Implementar `PydanticAiGraphExtractor`**
  - Integração do agente PydanticAI v2 + Gemini Flash-Lite com Rate Limiter, Semaphore, Retry com Backoff e Catálogo de Entidades.
- [ ] **Task 6: Testes Unitários e Mock do `PydanticAiGraphExtractor`**
  - Testar extração estruturada, fallback gracioso, reuso de entidades e recuperação de erro 429.

### Checkpoint: Extractor Validation
- [ ] Extrator com PydanticAI funcionando e testado com mocks e modelos reais.

### Phase 4: Configurações, Container IoC & Integração na Saga
- [ ] **Task 7: Atualizar `AppSettings`, Container IoC e `DocumentIngestionSagaCoordinator`**
  - Adicionar variáveis de configuração (`GEMINI_MAX_RPM`, `GEMINI_MAX_TPM`, `GEMINI_MAX_CONCURRENCY`), injetar `PydanticAiGraphExtractor` no container e conectar na Saga.
- [ ] **Task 8: Testes de Integração End-to-End da Extração**
  - Testar fluxo E2E com múltiplos Parent Chunks processados em paralelo.

### Phase 5: Quality Gates & Pre-Commit
- [ ] **Task 9: Execução dos Gates de Qualidade (`make pre-commit`)**
  - Pytest, Ruff linter, Ruff format e Mypy estrito.

### Checkpoint: Final
- [ ] Extrator completo aprovado no gate oficial e pronto para uso com a CF/88.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Estouro de cota da API do Gemini sob concorrência pesada | Alto | `AsyncTokenBucketLimiter` com sliding window estrito antes do disparo + retry exponencial com jitter |
| Entidades com pequenas variações de grafia gerarem nós duplicados | Médio | Injeção do catálogo de entidades existentes no prompt do PydanticAI com instrução explícita de normalização |
| Ausência de chave `GEMINI_API_KEY` em testes locais | Baixo | Fallback determinístico ou mock transparente quando a chave não estiver configurada |

---

## Open Questions
- Nenhuma. O modelo Gemini Flash-Lite oferece o balanço ideal de custo ($0.25/1M) e structured outputs via PydanticAI.
