# Lean 7B/8B Structured Ontology Extractor & Eval Suite

## 1. Problem Statement
**Como podemos extrair Knowledge Graphs complexos com alto throughput e baixo custo usando modelos 7B/8B com Structured Outputs diretos via OpenRouter, eliminando o overhead de frameworks agênticos (PydanticAI) e desacoplando a canonização de entidades para pós-processamento determinístico?**

---

## 2. Recomendação Arquitetural
Substituir a abordagem agêntica pesada (Gemma 4 26B com injeção in-prompt de 100 aliases e dependência do `PydanticAI`) por:
1. **[`DirectOpenRouterGraphExtractor`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/infrastructure/extractors/direct_openrouter_graph_extractor.py):**
   - Chamada direta de completion via OpenRouter / OpenAI SDK com `response_format: {"type": "json_object"}`.
   - Prompt de sistema focado estritamente na gramática da ontologia (nós permitidos, propriedades e relações válidas).
   - Validação direta e tipagem estrita via Pydantic v2.
2. **Desacoplamento da Resolução de Entidades:**
   - O LLM extrai spans crus sintáticos.
   - A canonização (aliases, deduplicação de nós) é delegada para algoritmos locais determinísticos (Cosine Similarity de embeddings + Levenshtein fuzzy match) no [`ExistingEntityRegistry`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/infrastructure/extractors/existing_entity_registry.py).
3. **Suite de Avaliação de Modelos ([`eval_graph_extractors.py`](file:///Users/insider/personal/agentic-substrate/scripts/eval_graph_extractors.py)):**
   - Testes automatizados cobrindo cenários de Baixa, Média e Alta complexidade.
   - Medição comparativa de latência (ms), integridade referencial de arestas, aderência à ontologia e conformidade sintática.

---

## 3. Hipóteses & Critérios de Validação

- [x] **Hipótese 1:** Modelos 7B/8B (Llama 3.1 8B, Qwen 2.5 7B) entregam 100% de JSONs válidos quando operam com `response_format: json_object` / *constrained decoding*.
- [x] **Hipótese 2:** A eliminação de wrappers de agentes reduz a latência de extração por chunk em até 3x a 5x.
- [ ] **Hipótese 3:** Em textos de alta complexidade, o Llama 3.1 8B mantém integridade referencial ($\ge 95\%$ de arestas com nós existentes) quando o prompt impõe a regra explicitamente.

---

## 4. Escopo do MVP (Spike Entregue)

- **Em escopo:**
  - Implementação de [`DirectOpenRouterGraphExtractor`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/infrastructure/extractors/direct_openrouter_graph_extractor.py) em conformidade com `IGraphExtractor`.
  - Suíte de avaliação multi-modelo com 3 cenários de complexidade (`scripts/eval_graph_extractors.py`).
  - Testes unitários com mock determinístico e fallback em [`test_direct_openrouter_graph_extractor.py`](file:///Users/insider/personal/agentic-substrate/tests/modules/knowledge/infrastructure/test_direct_openrouter_graph_extractor.py).
  - Rate limiting assíncrono via `AsyncTokenBucketLimiter`.

- **Fora de escopo (Not Doing e Racional):**
  - **Tool calling no LLM:** Não utilizar function calls para JSON puro (adiciona latência e falhas de formatação em modelos 7B).
  - **In-Prompt Alias Resolution:** Não injetar catálogos extensos de entidades prévias no prompt do LLM para evitar perda de atenção contextual (*lost-in-the-middle*).

---

## 5. Como Executar o Benchmark de Avaliação

### Com Chave de API (Live OpenRouter):
```bash
poetry run python scripts/eval_graph_extractors.py \
  --models "meta-llama/llama-3.1-8b-instruct,qwen/qwen-2.5-7b-instruct,google/gemma-4-26b-a4b-it" \
  --api-key "sk-or-v1-..."
```

### Em Modo Mock / Local:
```bash
poetry run python scripts/eval_graph_extractors.py --dry-run
```
