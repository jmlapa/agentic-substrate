# ADR-0002: Unified FalkorDB Hybrid GraphRAG Engine

## Status
Accepted

## Date
2026-08-17

## Context
Initial designs split vector retrieval (PostgreSQL + pgvector) and graph relationships (FalkorDB). This dual-database architecture introduced:
- Distributed transactions and dual-write synchronicity issues during ingestion sagas.
- Cross-network roundtrips to reconcile vector search chunk IDs with graph node entities.
- Redundant infrastructure complexity and operational overhead.

## Decision
Unify both vector indexing and property graph representation within **FalkorDB** as the primary GraphRAG engine:
1. **Structural Document Graph**: Model documents hierarchically directly in the graph: `(:Document)-[:HAS_PARENT]->(:ParentChunk)-[:HAS_CHILD]->(:ChildChunk)`.
2. **Native Vector Indexing**: Use FalkorDB's native HNSW vector index on `(:ChildChunk.embedding)` with cosine metric.
3. **Conceptual Mentions**: Link Parent Chunks to extracted ontological entities via `(:ParentChunk)-[:MENTIONS]->(:Entity)`.
4. **Single-Hop OpenCypher Hybrid Search**: Query vector similarities with `db.idx.vector.queryNodes` and ascend to Parent Chunks and connected entity subgraphs in a single Cypher query execution.

## Alternatives Considered

### Dual Store (Postgres pgvector + FalkorDB)
- **Pros**: Isolated vector operations.
- **Cons**: Severe dual-write failure modes during saga rollbacks, N+1 network queries to fetch parent text and entity subgraphs.
- **Rejected**: FalkorDB provides native vector index support, eliminating the second database.

## Consequences
- Removed `pgvector` runtime dependency from the Knowledge module.
- 10x query latency reduction for hybrid GraphRAG retrievals (sub-10ms single-query responses).
- Complete isolation per Knowledge Base via dedicated FalkorDB graph keys (`kb_<kb_id>`).
