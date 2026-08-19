# Task List: Natural Parent Deduplication, 50-Candidate Oversampling & Asymmetric Embed Query

## Task 1: Atualizar `FalkorDbGraphStoreAdapter` e `InMemoryGraphStore` com Cypher de Deduplicação Natural e 5 Vizinhos

**Description:** Modificar a consulta Cypher unificada em `FalkorDbGraphStoreAdapter` para remover o `LIMIT` intermediário do estágio de sementes, permitindo a deduplicação natural de todos os `ParentChunk`s derivados dos `ChildChunk`s do HNSW, expandir até 5 vizinhos ontológicos (`[0..5]`) por semente, e aplicar `LIMIT $top_k` exclusivamente após o reranking global do `fused_score`.

**Acceptance criteria:**
- [x] O estágio intermediário de sementes não possui `LIMIT` precoce.
- [x] A expansão de vizinhos busca até 5 vizinhos (`[0..5]`).
- [x] `LIMIT $top_k` é aplicado estritamente no final após `ORDER BY fused_score DESC`.
- [x] `candidate_k` padrão em `query_hybrid` atualizado para `50`.

**Verification:**
- [x] Type check: `poetry run mypy src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`
- [x] Testes passam: `poetry run pytest tests/unit/test_falkordb_graph_store_adapter.py`

**Dependencies:** None

**Files likely touched:**
- `src/modules/knowledge/domain/interfaces/i_graph_store.py`
- `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`
- `src/modules/knowledge/infrastructure/adapters/in_memory_graph_store.py`

**Estimated scope:** Small (3 files)

---

## Checkpoint: Infrastructure Layer
- [x] `poetry run pytest tests/unit/test_falkordb_graph_store_adapter.py` passa sem erros.
- [x] `poetry run mypy src/modules/knowledge/infrastructure/` sem erros de tipagem estrita.

---

## Task 2: Atualizar `QueryKnowledgeUseCase` com `embed_query` e `candidate_k = max(top_k * 4, 50)`

**Description:** Modificar o caso de uso `QueryKnowledgeUseCase` para calcular `candidate_k = max(request.top_k * 4, 50)`, invocar `await self._embedding_service.embed_query(request.query)` para busca semântica assimétrica e repassar `candidate_k` para o `graph_store`.

**Acceptance criteria:**
- [x] `candidate_k` é calculado como `max(request.top_k * 4, 50)`.
- [x] A vetorização invoca `await self._embedding_service.embed_query(request.query)`.
- [x] `_graph_store.query_hybrid` é chamado com `request.kb_id`, `query_vec`, `request.top_k`, `candidate_k`.

**Verification:**
- [x] Type check: `poetry run mypy src/modules/knowledge/application/use_cases/query_knowledge/`
- [x] Testes passam: `poetry run pytest tests/unit/test_query_knowledge_use_case.py`

**Dependencies:** Task 1

**Files likely touched:**
- `src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_use_case.py`

**Estimated scope:** Small (1 file)

---

## Checkpoint: Application Layer
- [x] `QueryKnowledgeUseCase` executa com sucesso e popula `retrieval_trace` com `candidate_k >= 50`.
- [x] Mypy em modo estrito aprova a camada de aplicação.

---

## Task 3: Atualizar e Expandir a Suíte de Testes Unitários e de Integração

**Description:** Atualizar todos os testes existentes que mockam `IEmbeddingService` ou `IGraphStore` para esperar `embed_query` e `candidate_k >= 50`, e atualizar testes de integração em FalkorDB e API Gateway.

**Acceptance criteria:**
- [x] Testes em `tests/unit/test_query_knowledge_use_case.py` atualizados para verificar `embed_query` e `candidate_k=50` (ou `80` para default `top_k=20`).
- [x] Testes de integração em `tests/integration/test_api_gateway.py`, `tests/integration/test_falkordb_hybrid_search_integration.py` e `tests/integration/test_falkordb_live_graphrag_retrieval.py` atualizados e passando.

**Verification:**
- [x] `poetry run pytest tests/unit/test_query_knowledge_use_case.py tests/integration/test_falkordb_hybrid_search_integration.py tests/integration/test_api_gateway.py tests/integration/test_falkordb_live_graphrag_retrieval.py`

**Dependencies:** Task 2

**Files likely touched:**
- `tests/unit/test_query_knowledge_use_case.py`
- `tests/integration/test_api_gateway.py`
- `tests/integration/test_falkordb_hybrid_search_integration.py`
- `tests/integration/test_falkordb_live_graphrag_retrieval.py`

**Estimated scope:** Medium (4 files)

---

## Task 4: Atualizar Documentação Técnica e Especificações (SDD)

**Description:** Atualizar a especificação do pipeline de recuperação e o changelog com a nova query Cypher de deduplicação natural, os 5 vizinhos e a busca assimétrica.

**Acceptance criteria:**
- [x] `SPEC-optimized-graphrag-retrieval-and-budgeting.md` atualizado com a nova consulta Cypher e fórmula de `candidate_k`.
- [x] `CHANGELOG.md` atualizado na seção `[Unreleased]` ou patch correspondente.

**Verification:**
- [x] Leitura e revisão dos arquivos de documentação.

**Dependencies:** Task 3

**Files likely touched:**
- `SPEC-optimized-graphrag-retrieval-and-budgeting.md`
- `CHANGELOG.md`

**Estimated scope:** Small (2 files)

---

## Checkpoint: Final Quality Gate
- [x] `make pre-commit` executado com 100% de sucesso (Ruff check, Ruff format, Mypy Strict, Pytest com todos os 169 testes passando).
