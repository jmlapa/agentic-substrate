# ADR-0003: PydanticAI v2 Graph Extraction, Rate Limiting and Cumulative Canonization

## Status
Superseded by ADR-0010 and ADR-0011

## Date
2026-08-17

## Context
Ontology extraction from unstructured Markdown requires extracting strongly-typed nodes and relationships complying with user-defined schemas without entity fragmentation (e.g., extracting "CF/88", "Constituição de 1988" as separate nodes) and without exceeding provider rate limits (e.g., Google Gemini 300 RPM, 1.000.000 TPM).

## Decision
1. **PydanticAI v2 Extraction**: Use PydanticAI `Agent` with `gemini-3.5-flash-lite` and dynamically constructed Pydantic models for structured output generation.
2. **Transport-Level Rate Limiting**: Intercept all outgoing HTTP requests using `RateLimitedAsyncTransport` wrapping `httpx.AsyncHTTPTransport` with a non-blocking 60-second sliding window Token Bucket limiter (`AsyncTokenBucketLimiter`).
3. **Cumulative Entity Canonization**: Inject existing extracted entities (`IEntityRegistry` / `ExistingEntityRegistry`) into the LLM system prompt per Knowledge Base to enforce ID reuse and avoid duplicate nodes across chunks.
4. **Concurrent Batching**: Process Parent Chunks in parallel via `asyncio.gather` bounded by a concurrency semaphore (`max_concurrency=15`).

## Alternatives Considered

### Unconstrained Parallel Calls
- **Pros**: Fastest code implementation.
- **Cons**: Triggers HTTP 429 ResourceExhausted immediately on large multi-page documents.
- **Rejected**: Rate limiter provides deterministic flow control.

### Post-Processing Entity Disambiguation
- **Pros**: Simpler extraction prompt.
- **Cons**: Quadratic graph clustering complexity after ingestion.
- **Rejected**: In-context cumulative entity catalog produces cleaner graph structures from the start.

## Consequences
- High-volume documents (e.g. 437 pages of the Brazilian Federal Constitution) ingest reliably within 1-2 minutes without API throttling errors.
- Clean, deduped knowledge graphs in FalkorDB.
