# Implementation Plan: DeepSeek-V4-Flash Fact-Dense RAG Synthesis & Dual-Payload

## Overview
Implementar a síntese RAG baseada em **DeepSeek-V4-Flash** via OpenRouter, gerando respostas em Markdown fact-dense com proveniência explícita (`[^chunk:<uuid>]` / `[^entidade:<tipo>:<nome>]`), eliminando dependências legadas de síntese no Gemini, e adicionando o modo dual de consulta (`mode: "synthesis" | "retrieve"`).

Isso atende dois públicos essenciais:
1. **Agentes Autônomos / Tools:** Consomem o modo `retrieve` (<30ms, zero custo de LLM) recebendo a lista de subgrafos e chunks diretamente para seus loops ReAct.
2. **Humanos / Interfaces (Console & Chatbots):** Consomem o modo `synthesis` recebendo um resumo Markdown conciso e factual + subgrafo inspecionável.

---

## Architecture Decisions
1. **`DeepSeekRagSynthesizer` (OpenRouter Gateway):**
   - Criação de `DeepSeekRagSynthesizer` em `src/modules/knowledge/infrastructure/adapters/deepseek_rag_synthesizer.py`.
   - Implementa a interface de domínio `ILlmSynthesisService`.
   - Utiliza `httpx.AsyncClient` consumindo `https://openrouter.ai/api/v1/chat/completions` com o modelo `deepseek/deepseek-v4-flash`, cabeçalhos de governança (`HTTP-Referer`, `X-Title`) e temperatura determinística (0.1).
2. **Dual-Mode Query Request Contract:**
   - Adicionar `mode: str = "synthesis"` em `QueryKnowledgeRequest` e no DTO `QueryKnowledgeDTO`.
   - `mode == "retrieve"`: pula a síntese de LLM e devolve a resposta imediata com a lista de evidências.
   - `mode == "synthesis"`: executa a busca híbrida + chamada ao sintetizador.
3. **Injeção de Dependências no `AppContainer`:**
   - Atualizar `src/api_gateway/container.py` para usar `DeepSeekRagSynthesizer` quando `OPENROUTER_API_KEY` estiver configurada, fallback para `InMemoryRagSynthesizer` em testes offline.
4. **Interface do Usuário (Playground Frontend):**
   - Atualizar `QueryPlaygroundView.tsx` para permitir alternar entre `Síntese Completa` e `Apenas Recuperação (Raw)`.

---

## Task List

### Phase 1: DeepSeek Rag Synthesizer Adapter (TDD)
- [ ] **Task 1: Implementar `DeepSeekRagSynthesizer`** (`src/modules/knowledge/infrastructure/adapters/deepseek_rag_synthesizer.py`)
- [ ] **Task 2: Testes Unitários de `DeepSeekRagSynthesizer`** (`tests/unit/test_deepseek_rag_synthesizer.py`)

### Checkpoint 1: Adaptador de Síntese
- [ ] Testes unitários do sintetizador passando com mock HTTP de OpenRouter.

### Phase 2: Dual-Mode Query Use Case & API Contract
- [ ] **Task 3: Atualizar DTOs e Request de Query** (`QueryKnowledgeRequest`, `QueryKnowledgeDTO`)
- [ ] **Task 4: Atualizar `QueryKnowledgeUseCase` com Fast-Path para `mode="retrieve"`**
- [ ] **Task 5: Testes Unitários do `QueryKnowledgeUseCase` nos Modos `synthesis` e `retrieve`**

### Checkpoint 2: Casos de Uso & API
- [ ] Todos os testes unitários do caso de uso passando.

### Phase 3: Container Wiring & Testes de Integração
- [ ] **Task 6: Atualizar `AppContainer` para Injetar `DeepSeekRagSynthesizer`**
- [ ] **Task 7: Testes de Integração da API de Query** (`tests/integration/test_knowledge_controller.py`)

### Phase 4: Frontend Console & Playground
- [ ] **Task 8: Atualizar `QueryPlaygroundView.tsx` e `types.ts` com Toggle de Modo e Badges de Proveniência**

### Phase 5: Especificação, ADR e Qualidade
- [ ] **Task 9: Criar `SPEC-deepseek-v4-fact-dense-rag-synthesis.md` e ADR-0007**
- [ ] **Task 10: Executar Gate Oficial de Qualidade (`make pre-commit`)**

---

## Risks and Mitigations
| Risk | Impact | Mitigation |
| :--- | :--- | :--- |
| Ausência de `OPENROUTER_API_KEY` em ambientes locais de teste | Médio | Fallback gracioso para `InMemoryRagSynthesizer` garantindo que testes e ambientes offline funcionem sem quebra. |
| Variação no formato de citação do LLM | Baixo | Prompt restritivo fornecendo exemplos claros de Markdown denso e `[^chunk:<uuid>]`. |
| Quebra de clientes legados que não enviam `mode` | Baixo | Default definido como `"synthesis"`, garantindo 100% de compatibilidade retroativa. |

---

## Open Questions
- *Nenhuma pendência impeditiva aberta. Todos os requisitos de proveniência e modo retrieve foram mapeados.*
