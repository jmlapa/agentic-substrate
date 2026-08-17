# Implementation Plan: Unified FalkorDB Hybrid GraphRAG & Structural Node Ingestion

## Overview
Unify knowledge storage, indexing, and querying directly into **FalkorDB**, creating a single hybrid graph per Knowledge Base that houses both the **structural document backbone** (`Document` ➔ `ParentChunk` ➔ `ChildChunk`) and **ontological entities** (`Mentions`). Hybrid search (vector KNN + subgraph expansion) will execute in a single OpenCypher query (`db.idx.vector.queryNodes`), removing read coupling from PostgreSQL and enabling parallelized chunk-level LLM extraction for large documents.

---

## Architecture Decisions

1. **One Graph per Knowledge Base (`kb_<kb_id>`)**:
   - Each Knowledge Base maps to a single FalkorDB graph instance.
   - Documents (`:Document`), parent chunks (`:ParentChunk`), child chunks (`:ChildChunk`), and ontology entities (`:Entity`) are all vertices/nodes inside this unified graph.
   - Relationships:
     - `(:Document)-[:HAS_PARENT]->(:ParentChunk)`
     - `(:ParentChunk)-[:CONTAINS_CHILD]->(:ChildChunk)`
     - `(:ParentChunk)-[:MENTIONS]->(:Entity)`
     - `(:Entity)-[:RELATION]->(:Entity)`

2. **Native FalkorDB Vector Indexing**:
   - Index vector embeddings directly on `(:ChildChunk)` nodes using `VECTOR INDEX FOR (c:ChildChunk) ON (c.embedding)` with dimension 768 (Gemini Embedding 2) and cosine similarity.

3. **Single Cypher Query Hybrid Search**:
   - Query KNN on `ChildChunk.embedding`, traverse up to `ParentChunk`, optionally expand connected `:MENTIONS` entities, and return deduplicated parent context with aggregated entities and similarity scores in one trip.

4. **Batch Extraction per `ParentChunk`**:
   - The saga coordinates LLM ontological extraction per `ParentChunk` (~1.000 tokens) rather than dumping full 250-page documents to the LLM, connecting extracted entities to their respective parent node via `[:MENTIONS]`.

5. **Strict Single Class per File & Type Safety**:
   - Every entity, value object, interface, adapter, and use case lives in its own dedicated file adhering to Mypy `strict = true` and the `Result[T, E]` pattern.

---

## Task List

### Phase 1: Domain Value Objects & Store Interface
- [ ] **Task 1: Domain Value Objects (`HybridSearchResult` & `StructuralGraphDocument`)**
- [ ] **Task 2: Interface Evolution (`IGraphStore` extensions)**

### Checkpoint: Domain Foundation
- [ ] Domain models and interfaces strictly typed and tested.

### Phase 2: FalkorDB & In-Memory Adapters
- [ ] **Task 3: Structural Ingestion & Vector Indexing in Graph Adapters**
- [ ] **Task 4: Unified Cypher Hybrid Query Implementation in Graph Adapters**

### Checkpoint: Adapter Capabilities
- [ ] Unit tests verify OpenCypher generation, vector index setup, and in-memory mock fidelity.

### Phase 3: Saga Coordination & Use Case Refactoring
- [ ] **Task 5: Batch Parent-Level Graph Extraction in `DocumentIngestionSagaCoordinator`**
- [ ] **Task 6: Refactor `QueryKnowledgeUseCase` for Single-Query Hybrid Search**

### Checkpoint: End-to-End Ingestion & Query Flow
- [ ] Full saga pipeline and query use case functioning in memory and with mocked FalkorDB.

### Phase 4: Integration Verification & Quality Gates
- [ ] **Task 7: Integration Tests, Pre-commit Gates & Documentation**

### Checkpoint: Quality Gate Complete
- [ ] `make pre-commit` passes with 0 errors (Ruff lint/format, Mypy strict, Pytest 100%).

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FalkorDB vector index syntax differences across versions | Medium | Wrap vector index creation in safe `CREATE VECTOR INDEX IF NOT EXISTS` or exception handling in adapter |
| Large document parent extraction concurrency limits | High | Process parent chunks in bounded asynchronous batches (`asyncio.gather` with semaphore) |
| Missing entities on chunks without ontological mentions | Low | Use `OPTIONAL MATCH (parent)-[:MENTIONS]->(entity)` in Cypher query to avoid dropping valid text chunks |

---

## Open Questions
- None. Graph granularity clarified: 1 Graph per Knowledge Base containing structural nodes + conceptual nodes.
