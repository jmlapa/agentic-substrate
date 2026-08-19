# Implementation Plan: Natural Parent Deduplication, 50-Candidate Oversampling & Asymmetric Embed Query

## Overview
Este plano consolida o refinamento definitivo do pipeline de recuperação (*GraphRAG*) do **Agentic Substrate**. A estratégia elimina completamente qualquer afunilamento precoce de sementes, operando com **oversampling fixado em `candidate_k = max(top_k * 4, 50)`**, deduplicação natural de todos os `ParentChunk`s derivados dos 50 filhos, expansão dos **5 vizinhos mais próximos por semente**, reranking híbrido global no pool completo e aplicação estrita do `LIMIT $top_k` apenas na saída final, além da adoção da busca assimétrica via `embed_query`.

---

## Architecture Decisions

1. **Eliminação do `LIMIT` Precoce & Deduplicação Natural de Sementes:**
   - **Decisão:** Não definir um parâmetro `seed_k` artificial. O conjunto de sementes é a projeção desduplicada natural dos 50 melhores `ChildChunk`s retornados pelo HNSW (`WITH p_seed, max(1.0 - vec_score)`).
   - **Oversampling de Filhos:** `candidate_k = max(request.top_k * 4, 50)` (mínimo de 50 nós `ChildChunk`).
   - **Expansão de Subgrafo:** Até 5 vizinhos fortemente conectados por semente (`[0..5]`).
   - **Corte Final Estrito:** O único `LIMIT` da query Cypher é o `LIMIT $top_k` executado após o cálculo do `fused_score` e ordenação global.
   - **Garantia Algorítmica:** O nó retornado na posição #1 quando `top_k=1` é idêntico ao 1º colocado quando `top_k=5`.

2. **Adoção Estrita de `embed_query` (Asymmetric Task Instruction):**
   - **Decisão:** `QueryKnowledgeUseCase` invoca `IEmbeddingService.embed_query(request.query)`.
   - **Formato:** `task: search result | query: {query}` (instrução oficial do Gemini 2 para busca assimétrica pergunta-resposta).

3. **Observabilidade Expandida no `retrieval_trace`:**
   - **Decisão:** O trace registra `candidate_k`, `top_k`, `mode`, `token_budget_limit`, `token_budget_consumed`, `budget_truncated`, `results_count` e `retrieval_sources`.

---

## Task List

### Phase 1: Infrastructure & Cypher Natural Deduplication
- [ ] Task 1: Atualizar `FalkorDbGraphStoreAdapter` com Cypher de Deduplicação Natural e 5 Vizinhos
  - Remover `LIMIT $top_k` do estágio intermediário de sementes.
  - Expandir vizinhos para `[0..5]`.
  - Manter `LIMIT $top_k` estrito apenas após o reranking global do `fused_score`.
  - Atualizar default de `candidate_k` para 50.

### Checkpoint: Infrastructure Layer
- [ ] Testes unitários do `FalkorDbGraphStoreAdapter` e `InMemoryGraphStore` passando.

---

### Phase 2: Application Layer & Asymmetric Embedding Integration
- [ ] Task 2: Atualizar `QueryKnowledgeUseCase` com `embed_query` e `candidate_k = max(top_k * 4, 50)`
  - Modificar cálculo de `candidate_k` para `max(request.top_k * 4, 50)`.
  - Invocar `await self._embedding_service.embed_query(request.query)`.
  - Repassar `candidate_k` para `_graph_store.query_hybrid`.

### Checkpoint: Application Layer
- [ ] Testes unitários de `QueryKnowledgeUseCase` atualizados e passando com 100% de cobertura.

---

### Phase 3: Test Suite Updates & Specifications Alignment
- [ ] Task 3: Atualizar e Expandir a Suíte de Testes Unitários e de Integração
  - Atualizar mocks em `tests/unit/test_query_knowledge_use_case.py` para `embed_query` e `candidate_k=50`.
  - Adicionar teste unitário de invariância comprovando que `top_k=1` e `top_k=5` avaliam o mesmo pool de sementes desduplicadas e produzem o mesmo campeão no topo.
  - Atualizar testes de integração em `tests/integration/test_api_gateway.py` e `tests/integration/test_falkordb_live_graphrag_retrieval.py`.

- [ ] Task 4: Atualizar Documentação Técnica e Especificações (SDD)
  - Atualizar `SPEC-optimized-graphrag-retrieval-and-budgeting.md` com a nova query Cypher e descrição da busca assimétrica.
  - Registrar no `CHANGELOG.md`.

### Checkpoint: Final Quality Gate
- [ ] Executar `make pre-commit` (Ruff, Mypy Strict, Pytest com 100% de aprovação).

---

## Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|:---:|---|
| Aumento de vizinhos para 5 por semente | Baixo | FalkorDB avalia em memória C via GraphBLAS (~3ms para ~100 candidatos). |
| Bases com menos de 50 chunks | Nenhum | HNSW e Cypher operam com limites superiores, tratando bases pequenas de forma transparente. |
