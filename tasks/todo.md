# Tasks: Unified FalkorDB Hybrid GraphRAG & Structural Ingestion

## Phase 1: Domain Foundation & Value Objects

- [x] Task 1: Domain Value Objects (`HybridSearchResult` & `StructuralGraphDocument`)
  - **Description:** Implement `HybridSearchResult` and `StructuralGraphDocument` value objects in the domain layer, following Single Class per File and strict typing.
  - **Acceptance Criteria:**
    - `HybridSearchResult` contains `parent_chunk_id`, `header_path`, `parent_content`, `relevance_score`, and `related_entities: list[dict[str, Any]]`.
    - `StructuralGraphDocument` encapsulates document id, name, parent chunks, and child chunks with embeddings.
    - Exported cleanly in `src/modules/knowledge/domain/value_objects/__init__.py`.
  - **Verification:**
    - Unit tests in `tests/unit/test_knowledge_value_objects.py` validate immutability and attributes.
    - `uv run mypy src/modules/knowledge/domain` passes without errors.
  - **Dependencies:** None
  - **Files:**
    - `src/modules/knowledge/domain/value_objects/hybrid_search_result.py`
    - `src/modules/knowledge/domain/value_objects/structural_graph_document.py`
    - `src/modules/knowledge/domain/value_objects/__init__.py`
    - `tests/unit/test_knowledge_value_objects.py`
  - **Scope:** S (3-4 files)

- [x] Task 2: Interface Evolution (`IGraphStore` extensions)
  - **Description:** Extend `IGraphStore` protocol with methods for vector index initialization, structural document storage, parent-entity mentions storage, and hybrid search.
  - **Acceptance Criteria:**
    - `IGraphStore` declares:
      - `ensure_vector_index(kb_id: UUID, dimension: int, similarity_function: str) -> None`
      - `store_structural_document(kb_id: UUID, document: StructuralGraphDocument) -> tuple[int, int]`
      - `store_parent_mentions(kb_id: UUID, parent_chunk_id: str, graph: ExtractedGraph) -> tuple[int, int]`
      - `query_hybrid(kb_id: UUID, query_embedding: list[float], top_k: int) -> list[HybridSearchResult]`
    - Signatures conform to async/await and strict typing.
  - **Verification:**
    - `uv run mypy src/modules/knowledge/domain/interfaces` passes.
  - **Dependencies:** Task 1
  - **Files:**
    - `src/modules/knowledge/domain/interfaces/i_graph_store.py`
    - `src/modules/knowledge/domain/interfaces/__init__.py`
  - **Scope:** S (2 files)

---

## Checkpoint 1: Domain Foundation Complete
- [x] Value objects and store interfaces defined and verified with Mypy strict.

---

## Phase 2: Graph Adapters Implementation

- [x] Task 3: Structural Ingestion & Vector Indexing in Graph Adapters
  - **Description:** Implement `ensure_vector_index`, `store_structural_document`, and `store_parent_mentions` in `FalkorDbGraphStoreAdapter` and `InMemoryGraphAndVectorStore`.
  - **Acceptance Criteria:**
    - `FalkorDbGraphStoreAdapter` creates `(:ChildChunk)` vector index using OpenCypher vector index commands.
    - Ingests `(:Document)`, `(:ParentChunk)`, and `(:ChildChunk)` with `[:HAS_PARENT]` and `[:CONTAINS_CHILD]` edges.
    - Connects extracted entities to `ParentChunk` using `[:MENTIONS]` edges.
    - `InMemoryGraphAndVectorStore` implements corresponding in-memory operations for testing.
  - **Verification:**
    - `tests/unit/test_falkordb_graph_store_adapter.py` passes.
  - **Dependencies:** Task 2
  - **Files:**
    - `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`
    - `src/modules/knowledge/infrastructure/adapters/in_memory_graph_and_vector_store.py`
    - `tests/unit/test_falkordb_graph_store_adapter.py`
  - **Scope:** M (3 files)

- [x] Task 4: Unified Cypher Hybrid Query Implementation
  - **Description:** Implement `query_hybrid` in `FalkorDbGraphStoreAdapter` using `db.idx.vector.queryNodes`, traversing up to `ParentChunk` and expanding `[:MENTIONS]` entities.
  - **Acceptance Criteria:**
    - Executes single OpenCypher query yielding `HybridSearchResult` objects sorted by relevance score.
    - Deduplicates parent chunks and aggregates related entities.
    - Handles cases where chunks have zero entity mentions without failing or omitting text.
    - `InMemoryGraphAndVectorStore` simulates cosine similarity and graph expansion.
  - **Verification:**
    - `tests/unit/test_falkordb_graph_store_adapter.py` validates Cypher query generation and row mapping.
  - **Dependencies:** Task 3
  - **Files:**
    - `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`
    - `src/modules/knowledge/infrastructure/adapters/in_memory_graph_and_vector_store.py`
    - `tests/unit/test_falkordb_graph_store_adapter.py`
  - **Scope:** S (3 files)

---

## Checkpoint 2: Adapters Complete & Tested
- [x] FalkorDB and InMemory adapters pass all unit tests with 100% coverage.

---

## Phase 3: Saga Pipeline & Use Case Integration

- [x] Task 5: Batch Parent-Level Graph Extraction in `DocumentIngestionSagaCoordinator`
  - **Description:** Refactor `DocumentIngestionSagaCoordinator` to generate child embeddings, store structural nodes in `IGraphStore`, and extract conceptual graph entities per `ParentChunk` with `[:MENTIONS]` links.
  - **Acceptance Criteria:**
    - Long documents are split into `ParentChunk` and `ChildChunk`.
    - `IGraphStore.store_structural_document` is called to create the structural graph backbone.
    - LLM extraction runs per `ParentChunk` in batches/concurrency and links entities via `store_parent_mentions`.
    - No monolithic full-document prompt sent to LLM for long texts.
  - **Verification:**
    - `tests/unit/test_document_ingestion_saga_coordinator.py` passes with parent-level extraction asserts.
  - **Dependencies:** Task 4
  - **Files:**
    - `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`
    - `tests/unit/test_document_ingestion_saga_coordinator.py`
  - **Scope:** M (2 files)

- [x] Task 6: Refactor `QueryKnowledgeUseCase` for Single-Query Hybrid Search
  - **Description:** Update `QueryKnowledgeUseCase`, Request, and Response to use `IEmbeddingService` for query embedding and `IGraphStore.query_hybrid` for retrieving unified results.
  - **Acceptance Criteria:**
    - `QueryKnowledgeUseCase` embeds search query via `IEmbeddingService`.
    - Calls `IGraphStore.query_hybrid(kb_id, query_embedding, top_k)`.
    - Returns `QueryKnowledgeResponse` containing list of `HybridSearchResult`.
  - **Verification:**
    - `tests/unit/test_query_knowledge_use_case.py` passes.
  - **Dependencies:** Task 5
  - **Files:**
    - `src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_request.py`
    - `src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_response.py`
    - `src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_use_case.py`
    - `tests/unit/test_query_knowledge_use_case.py`
  - **Scope:** M (4 files)

---

## Checkpoint 3: End-to-End Flow Validated
- [x] Saga ingestion and Hybrid Query Use Case execute end-to-end.

---

## Phase 4: Integration Verification & Quality Gates

- [x] Task 7: Integration Tests, Pre-commit Gates & Documentation
  - **Description:** Add integration verification tests, update module facades/container wiring, update `CHANGELOG.md`, and execute full quality gate.
  - **Acceptance Criteria:**
    - `api_gateway/container.py` wires the updated `QueryKnowledgeUseCase` with embedding service and graph store.
    - `CHANGELOG.md` updated with `Added` and `Changed` sections under `Unreleased`.
    - `make pre-commit` passes with 0 errors (Ruff lint, Ruff format, Mypy strict, Pytest 100%).
  - **Verification:**
    - Run `make pre-commit`.
  - **Dependencies:** Task 6
  - **Files:**
    - `src/api_gateway/container.py`
    - `CHANGELOG.md`
    - `tests/integration/test_falkordb_hybrid_search_integration.py`
  - **Scope:** M (3-4 files)

---

## Final Checkpoint
- [x] 100% Quality Gates Passing (`make pre-commit`).
- [x] Single Class per File strictly respected.
- [x] Documentation and specs synchronized.
