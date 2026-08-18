# Task List: DeepSeek-V4-Flash Fact-Dense RAG Synthesis & Dual-Payload

## Phase 1: DeepSeek Rag Synthesizer Adapter (TDD)

### Task 1: Implementar `DeepSeekRagSynthesizer`
- **Description:** Criar o adaptador `DeepSeekRagSynthesizer` em `src/modules/knowledge/infrastructure/adapters/deepseek_rag_synthesizer.py` implementando `ILlmSynthesisService`. O serviço formata o contexto híbrido (chunks estruturados e entidades do subgrafo) e invoca a API do OpenRouter (`deepseek/deepseek-v4-flash`) com prompt fact-dense focado em bullets e citações explícitas.
- **Acceptance criteria:**
  - [x] Implementa Single Class per File (`DeepSeekRagSynthesizer`).
  - [x] Usa `httpx.AsyncClient` com headers `HTTP-Referer` e `X-Title`.
  - [x] Exporta no `__init__.py` da pasta `adapters`.
- **Verification:**
  - [x] Command: `uv run mypy src/modules/knowledge/infrastructure/adapters/deepseek_rag_synthesizer.py`
- **Dependencies:** None
- **Files touched:**
  - `src/modules/knowledge/infrastructure/adapters/deepseek_rag_synthesizer.py`
  - `src/modules/knowledge/infrastructure/adapters/__init__.py`
- **Estimated scope:** Medium (2 files)

---

### Task 2: Testes Unitários de `DeepSeekRagSynthesizer`
- **Description:** Criar testes unitários em `tests/unit/test_deepseek_rag_synthesizer.py` cobrindo cenários com busca vazia, resposta bem-sucedida do OpenRouter com formatação Markdown, fallback em caso de erro HTTP e injeção de `httpx.AsyncClient` mockado.
- **Acceptance criteria:**
  - [x] 100% de cobertura nos métodos do adaptador.
  - [x] Zero chamadas de rede reais nos testes unitários.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/test_deepseek_rag_synthesizer.py`
- **Dependencies:** Task 1
- **Files touched:**
  - `tests/unit/test_deepseek_rag_synthesizer.py`
- **Estimated scope:** Small (1 file)

---

## Checkpoint 1: Adaptador de Síntese
- [x] Testes unitários do `DeepSeekRagSynthesizer` passando.
- [x] Validação de tipos do Mypy limpa no módulo do adaptador.

---

## Phase 2: Dual-Mode Query Use Case & API Contract

### Task 3: Atualizar DTOs e Request de Query
- **Description:** Adicionar campo opcional `mode: str = "synthesis"` em `QueryKnowledgeRequest` e `QueryKnowledgeDTO` para suportar `"synthesis"` e `"retrieve"`.
- **Acceptance criteria:**
  - [x] `QueryKnowledgeDTO` e `QueryKnowledgeRequest` tipados com default `"synthesis"`.
  - [x] Compatibilidade retroativa mantida para requisições existentes.
- **Verification:**
  - [x] Command: `uv run mypy src/api_gateway/dtos/query_knowledge_dto.py src/modules/knowledge/application/use_cases/query_knowledge/`
- **Dependencies:** None
- **Files touched:**
  - `src/api_gateway/dtos/query_knowledge_dto.py`
  - `src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_request.py`
- **Estimated scope:** Small (2 files)

---

### Task 4: Atualizar `QueryKnowledgeUseCase` com Fast-Path para `mode="retrieve"`
- **Description:** Modificar `QueryKnowledgeUseCase` para avaliar `request.mode`. Se `mode == "retrieve"`, pula o `synthesis_service` e retorna imediatamente os resultados recuperados (`answer` informativa/curta com total de evidências). Se `mode == "synthesis"`, chama o `synthesis_service.synthesize_answer`.
- **Acceptance criteria:**
  - [x] Fast-path executado quando `mode == "retrieve"`.
  - [x] Síntese executada quando `mode == "synthesis"`.
  - [x] Tratamento gracioso quando nenhum resultado for encontrado.
- **Verification:**
  - [x] Command: `uv run mypy src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_use_case.py`
- **Dependencies:** Task 3
- **Files touched:**
  - `src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_use_case.py`
- **Estimated scope:** Small (1 file)

---

### Task 5: Testes Unitários do `QueryKnowledgeUseCase`
- **Description:** Atualizar e expandir os testes unitários do caso de uso em `tests/unit/test_query_knowledge_use_case.py` para validar ambos os fluxos (`synthesis` e `retrieve`).
- **Acceptance criteria:**
  - [x] Teste validando que `mode == "retrieve"` não chama o `synthesis_service`.
  - [x] Teste validando que `mode == "synthesis"` chama o sintetizador corretamente.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/test_query_knowledge_use_case.py`
- **Dependencies:** Task 4
- **Files touched:**
  - `tests/unit/test_query_knowledge_use_case.py`
- **Estimated scope:** Small (1 file)

---

## Checkpoint 2: Casos de Uso & API
- [x] Testes do caso de uso executando com 100% de sucesso.

---

## Phase 3: Container Wiring & Testes de Integração

### Task 6: Atualizar `AppContainer` para Injetar `DeepSeekRagSynthesizer`
- **Description:** Ajustar `src/api_gateway/container.py` para instanciar `DeepSeekRagSynthesizer` usando `cfg.openrouter_api_key` e `cfg.openrouter_graph_model_name` (ou fallback para `InMemoryRagSynthesizer` se a chave não existir).
- **Acceptance criteria:**
  - [x] `DeepSeekRagSynthesizer` instanciado com as configurações do OpenRouter.
  - [x] Mypy strict satisfeito sem nenhum `Any` implícito.
- **Verification:**
  - [x] Command: `uv run mypy src/api_gateway/container.py`
- **Dependencies:** Task 1, Task 4
- **Files touched:**
  - `src/api_gateway/container.py`
- **Estimated scope:** Small (1 file)

---

### Task 7: Testes de Integração da API de Query
- **Description:** Atualizar `tests/integration/test_knowledge_controller.py` para testar queries com payload contendo `mode="retrieve"` e `mode="synthesis"`.
- **Acceptance criteria:**
  - [x] Endpoint `/api/v1/knowledge/bases/{kb_id}/query` responde com 200 OK para ambos os modos.
- **Verification:**
  - [x] Command: `uv run pytest tests/integration/test_api_gateway.py`
- **Dependencies:** Task 6
- **Files touched:**
  - `tests/integration/test_api_gateway.py`
- **Estimated scope:** Small (1 file)

---

## Phase 4: Frontend Console & Playground

### Task 8: Atualizar `QueryPlaygroundView.tsx` e `types.ts`
- **Description:** Atualizar o frontend para adicionar seletor de modo (`Síntese Fact-Dense (DeepSeek)` vs `Apenas Recuperação (Retrieve)`) e estilizar a exibição da síntese com proveniência.
- **Acceptance criteria:**
  - [x] `QueryKnowledgeDTO` atualizado em `frontend/src/api/types.ts`.
  - [x] Toggle de modo interativo no playground.
  - [x] Suporte à renderização limpa do markdown e evidências.
- **Verification:**
  - [x] Command: `npm --prefix frontend run build` (ou checagem de tipos/componente)
- **Dependencies:** Task 7
- **Files touched:**
  - `frontend/src/api/types.ts`
  - `frontend/src/pages/playground/QueryPlaygroundView.tsx`
  - `frontend/src/pages/playground/AnswerView.tsx`
- **Estimated scope:** Medium (3 files)

---

## Phase 5: Especificação, ADR e Qualidade

### Task 9: Criar `SPEC-deepseek-v4-fact-dense-rag-synthesis.md` e ADR-0007
- **Description:** Documentar a decisão arquitetural e a especificação técnica do sintetizador e do modo retrieve, atualizando `CAPABILITY-MAP.md` e `CHANGELOG.md`.
- **Acceptance criteria:**
  - [x] `SPEC-deepseek-v4-fact-dense-rag-synthesis.md` criado.
  - [x] ADR-0007 registrado em `docs/decisions/`.
  - [x] `CAPABILITY-MAP.md` e `CHANGELOG.md` sincronizados.
- **Verification:**
  - [x] Documentos criados e links validados.
- **Dependencies:** Task 8
- **Files touched:**
  - `SPEC-deepseek-v4-fact-dense-rag-synthesis.md`
  - `docs/decisions/0007-deepseek-v4-fact-dense-rag-synthesis.md`
  - `CAPABILITY-MAP.md`
  - `CHANGELOG.md`
- **Estimated scope:** Medium (4 files)

---

### Task 10: Executar Gate Oficial de Qualidade (`make pre-commit`)
- **Description:** Executar o gate completo do repositório para garantir zero erros de lint, formato, tipagem Mypy e 100% de cobertura nos testes.
- **Acceptance criteria:**
  - [x] Ruff check & format passam com zero avisos.
  - [x] Mypy em modo strict passa com zero erros.
  - [x] 100% dos testes unitários e de integração passando.
- **Verification:**
  - [x] Command: `make pre-commit`
- **Dependencies:** Tasks 1-9
- **Files touched:** All project files
- **Estimated scope:** Small (0 code modifications if clean)

