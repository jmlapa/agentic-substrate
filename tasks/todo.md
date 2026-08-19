# Task List: Optimized GraphRAG Retrieval, Candidate Fusion & Token Budgeting

## Phase 1: Domain Contracts & DTOs

- [x] **Task 1.1: Atualizar Value Object `HybridSearchResult`**
  - **Description:** Expandir o Value Object imutável [`HybridSearchResult`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/domain/value_objects/hybrid_search_result.py) adicionando os campos `document_id: str`, `document_name: str`, `retrieval_source: str = "vector_match"`, `prev_chunk_id: str | None = None`, `next_chunk_id: str | None = None` e `related_triples: list[str] = Field(default_factory=list)`.
  - **Acceptance:**
    - [x] `HybridSearchResult` herda de `ValueObject` com todos os novos campos tipados e imutáveis.
    - [x] Mypy strict passa sem erros.
  - **Verify:** `uv run mypy src/modules/knowledge/domain/value_objects/hybrid_search_result.py`
  - **Files:** `src/modules/knowledge/domain/value_objects/hybrid_search_result.py`

- [x] **Task 1.2: Atualizar Interface `IGraphStore`**
  - **Description:** Atualizar a assinatura do método `query_hybrid` na interface [`IGraphStore`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/domain/interfaces/i_graph_store.py) para aceitar `candidate_k: int = 20` e retornar `list[HybridSearchResult]`.
  - **Acceptance:**
    - [x] Método `query_hybrid(self, kb_id: UUID, query_embedding: list[float], top_k: int = 3, candidate_k: int = 20) -> list[HybridSearchResult]` tipado no protocolo `@runtime_checkable`.
  - **Verify:** `uv run mypy src/modules/knowledge/domain/interfaces/i_graph_store.py`
  - **Files:** `src/modules/knowledge/domain/interfaces/i_graph_store.py`

- [x] **Task 1.3: Atualizar DTOs de Request e Response (`QueryKnowledgeRequest`, `QueryKnowledgeResponse`, `QueryKnowledgeDTO`)**
  - **Description:** Adicionar parâmetros `max_tokens_budget: int = Field(default=3500, ge=50, le=32000)` e `include_graph_triples: bool = True` nos DTOs de entrada e `total_tokens_estimated: int = 0`, `matched_entities_in_query: list[str] = Field(default_factory=list)` e `retrieval_trace: dict[str, Any]` no DTO de resposta.
  - **Acceptance:**
    - [x] `QueryKnowledgeRequest` e `QueryKnowledgeDTO` com default `top_k=3` e validação de `max_tokens_budget` até 32k.
    - [x] `QueryKnowledgeResponse` com `total_tokens_estimated`, `matched_entities_in_query` e `retrieval_trace`.
  - **Verify:** `uv run mypy src/api_gateway/dtos/query_knowledge_dto.py src/modules/knowledge/application/use_cases/query_knowledge/`
  - **Files:**
    - `src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_request.py`
    - `src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_response.py`
    - `src/api_gateway/dtos/query_knowledge_dto.py`

---

### Checkpoint: Phase 1 (Domain Contracts & DTOs)
- [x] Mypy estrito passa sem erros nos arquivos de domínio e DTOs.
- [x] Single Class per File respeitado rigorosamente.

---

## Phase 2: Graph Store & Cypher Engine

- [x] **Task 2.1: Implementar Arestas Sequenciais `[:NEXT]` no `FalkorDbGraphStoreAdapter`**
  - **Description:** No método `_store_structural_document_sync` de [`FalkorDbGraphStoreAdapter`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py), adicionar a criação das arestas direcionadas `(p1:ParentChunk)-[:NEXT]->(p2:ParentChunk)` entre chunks consecutivos da lista `document.parents`.
  - **Acceptance:**
    - [x] Chunks consecutivos são ligados via aresta `[:NEXT]` no grafo FalkorDB.
    - [x] Casos com 0 ou 1 parent executam sem erro.
  - **Verify:** `uv run pytest tests/unit/test_falkordb_graph_store_adapter.py`
  - **Files:** `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`

- [x] **Task 2.2: Implementar Query Cypher com Expansão para 9 Candidatos, Reranking Global e Triplas**
  - **Description:** Reescrever `_query_hybrid_sync` em [`FalkorDbGraphStoreAdapter`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py):
    1. Busca $candidate\_k = \max(top\_k \times 4, 20)$ no índice HNSW de `ChildChunk` e obtém as $top\_k$ (3) sementes de `ParentChunk`.
    2. Expande até 2 vizinhos por semente via `[:MENTIONS]` $\rightarrow$ Universo expandido de até 9 candidatos.
    3. Unifica e aplica Reranking Global (`fused_score = base_score + (shared_entities * 0.10)`).
    4. Aplica `LIMIT $top_k` para selecionar os TOP-3 campeões absolutos do universo de 9.
    5. Projeta `prev_p.id AS prev_chunk_id`, `next_p.id AS next_chunk_id`, `d.id AS document_id`, `d.name AS document_name`, triplas relacionais e monta `list[HybridSearchResult]`.
  - **Acceptance:**
    - [x] `top_k=3` avalia até 9 candidatos (3 sementes + 6 vizinhos de grafo) e retorna estritamente os 3 mais relevantes.
    - [x] Se um vizinho de grafo superar uma semente vetorial fraca, ele assume uma das 3 vagas.
    - [x] Triplas relacionais (até 5 por chunk) e prev/next IDs populados corretamente.
  - **Verify:** `uv run pytest tests/unit/test_falkordb_graph_store_adapter.py`
  - **Files:** `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`

- [x] **Task 2.3: Atualizar `InMemoryGraphStore` para Testes Unitários**
  - **Description:** Atualizar o mock [`InMemoryGraphStore`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/infrastructure/adapters/in_memory_graph_store.py) para simular `prev_chunk_id`, `next_chunk_id`, `related_triples` e score de relevância ponderado.
  - **Acceptance:**
    - [x] `InMemoryGraphStore.query_hybrid` retorna `HybridSearchResult` compatível com os novos campos.
  - **Verify:** `uv run pytest tests/unit/`
  - **Files:** `src/modules/knowledge/infrastructure/adapters/in_memory_graph_store.py`

---

### Checkpoint: Phase 2 (Graph Store & Adapters)
- [x] Testes unitários do adapter FalkorDB e InMemory passando.
- [x] Verificação de queries Cypher sem erros de sintaxe.

---

## Phase 3: Application Use Case & Fact-Dense Synthesis

- [x] **Task 3.1: Implementar Dynamic Token Budgeting e Execution Trace no `QueryKnowledgeUseCase`**
  - **Description:** Em [`QueryKnowledgeUseCase`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_use_case.py):
    1. Passar `candidate_k = max(request.top_k * 4, 20)` para `query_hybrid`.
    2. Calcular contagem estimada de tokens dos resultados ($\sum \text{ceil}(\text{len}(p.\text{content}) / 3.3)$).
    3. Se o total exceder `request.max_tokens_budget`, truncar suavemente os chunks secundários (#3 em diante) preservando cabeçalhos e chunks primários.
    4. Preencher `total_tokens_estimated`, `retrieval_trace` e devolver `QueryKnowledgeResponse`.
  - **Acceptance:**
    - [x] O payload retornado nunca ultrapassa `request.max_tokens_budget` (até 32k).
    - [x] O modo `retrieve` retorna em tempo mínimo (< 30ms) sem chamada à LLM.
    - [x] O trace de observabilidade registra todos os parâmetros de execução.
  - **Verify:** `uv run pytest tests/unit/test_query_knowledge_use_case.py`
  - **Files:** `src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_use_case.py`

- [x] **Task 3.2: Atualizar `OpenRouterRagSynthesizer` (Gemma 4) com Injeção de Triplas Semânticas e Tags XML**
  - **Description:** Atualizar `_build_context` em [`OpenRouterRagSynthesizer`](file:///Users/insider/personal/agentic-substrate/src/modules/knowledge/infrastructure/adapters/openrouter_rag_synthesizer.py) para formatar as `related_triples` e entidades dentro de tags `<evidence>` com `<structured_facts>`.
  - **Acceptance:**
    - [x] Prompt de contexto inclui fatos relacionais formatados sob tags XML rígidas para defesa contra prompt injection.
    - [x] Modelo padrão configurado como Google Gemma 4 (`google/gemma-4-26b-a4b-it`).
  - **Verify:** `uv run pytest tests/unit/test_openrouter_rag_synthesizer.py`
  - **Files:** `src/modules/knowledge/infrastructure/adapters/openrouter_rag_synthesizer.py`


---

### Checkpoint: Phase 3 (Use Case & Synthesis)
- [x] Testes unitários do caso de uso cobrindo modos `retrieve`, `synthesis`, corte por token budget e resultados vazios.

---

## Phase 4: Verification & Quality Gate

- [x] **Task 4.1: Atualizar e Expandir a Suíte de Testes Unitários e de Integração**
  - **Description:** Adicionar casos de teste em `tests/unit/test_query_knowledge_use_case.py`, `tests/unit/test_falkordb_graph_store_adapter.py` e `tests/unit/test_deepseek_rag_synthesizer.py`.
  - **Acceptance:**
    - [x] 100% dos testes unitários e de integração passando com 90% de cobertura geral.
  - **Verify:** `uv run pytest --cov=src --cov-report=term-missing -v`
  - **Files:**
    - `tests/unit/test_query_knowledge_use_case.py`
    - `tests/unit/test_falkordb_graph_store_adapter.py`
    - `tests/unit/test_deepseek_rag_synthesizer.py`

- [x] **Task 4.2: Executar Gate Oficial de Qualidade (`make pre-commit`)**
  - **Description:** Executar linters, formatadores e checagem estrita de tipos do projeto.
  - **Acceptance:**
    - [x] Ruff check 0 erros e 0 warnings.
    - [x] Ruff format 100% conforme.
    - [x] Mypy `strict = true` sem nenhum erro (`No issues found`).
  - **Verify:** `make pre-commit`

