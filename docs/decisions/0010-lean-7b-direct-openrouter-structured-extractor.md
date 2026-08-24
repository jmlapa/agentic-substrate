# ADR-0010: Lean 7B/8B Structured Ontology Extractor via Direct OpenRouter JSON Completion

## Status
Accepted (Refines and supersedes the LLM extraction engine from ADR-0003 for OpenRouter)

## Date
2026-08-24

## Context
Initial iterations of the ontology graph extractor utilized `PydanticAI` with larger models (such as `google/gemma-4-26b-a4b-it`) and injected extensive catalogs of up to 100 known entities into the system prompt to enforce entity resolution during extraction.

Empirical benchmarks and latency profiling revealed several architectural bottlenecks:
1. **High Latency & Token Costs**: Larger 26B+ models introduced latencies of 4s to 15s per chunk and had elevated costs per million tokens.
2. **Framework Overhead**: Enveloping a single-step deterministic JSON extraction task in an agentic framework (`PydanticAI`) resulted in nested tool-calling abstractions, internal prompt bloating, and parsing overhead.
3. **In-Prompt Cognitive Load**: Feeding large lists of existing entities into the prompt distracted smaller models from identifying fine-grained relationships and caused structural instability in complex passages.

## Decision
1. **Direct Structured JSON Completion (`DirectOpenRouterGraphExtractor`)**:
   - Implement `IGraphExtractor` using direct completion calls to OpenRouter (`response_format={"type": "json_object"}`) without agent framework wrappers.
   - Leverage provider-level constrained decoding for guaranteed JSON schema syntax.
2. **Model Selection**: Elect **`meta-llama/llama-3.1-8b-instruct`** as the default ontology graph extraction model (`OPENROUTER_GRAPH_MODEL_NAME`).
3. **Lean Semantic Prompts**:
   - System prompts are strictly focused on ontology node definitions, properties, and allowable relationship types.
   - Decouple entity resolution and alias deduplication from the LLM prompt, delegating them to local deterministic algorithms (vector cosine similarity and Levenshtein fuzzy matching).
4. **Referential Integrity Enforcement**:
   - Explicitly enforce referential consistency in the adapter: any relationship whose `source_id` or `target_id` does not exist in the extracted entities list is automatically pruned before graph persistence.
5. **Multi-Complexity Evaluation Suite**:
   - Add [`scripts/eval_graph_extractors.py`](file:///Users/insider/personal/agentic-substrate/scripts/eval_graph_extractors.py) covering Low, Medium, and High complexity legal scenarios to continuously benchmark models against latency, referential integrity, and ontology schema adherence.

## Alternatives Considered

### Retaining Gemma 4 26B with PydanticAI
- **Pros**: Established setup.
- **Cons**: High latency (up to 15.1s per medium chunk), higher inference costs, and syntax failures on dense paragraphs (e.g. embedding booleans in entity arrays).
- **Rejected**: Llama 3.1 8B demonstrated 100% integrity with up to 30x lower latency (501ms on medium passages).

### Qwen 2.5 7B Instruct
- **Pros**: Fast and accurate node extraction.
- **Cons**: Overly conservative relationship linking (identified ~40% fewer edges in dense scenarios compared to Llama 3.1 8B).
- **Rejected**: Llama 3.1 8B captured 8 nodes and 7 edges with 100% referential integrity in high-complexity texts.

## Consequences
- **Throughput & Latency**: Sub-second extraction per chunk on standard text, enabling rapid ingestion pipelines.
- **Cost Reduction**: ~85% reduction in token costs for Knowledge Graph extraction.
- **Maintainability**: Clear, readable single-class adapter compliant with clean architecture principles.
