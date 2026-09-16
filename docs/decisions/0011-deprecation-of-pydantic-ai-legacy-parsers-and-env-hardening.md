# ADR-0011: Deprecation of PydanticAI, Legacy Parsers/Chunkers, and Environment Hardening

## Status
Accepted (Formally supersedes ADR-0003 and prunes superseded adapters from ADR-0004 and ADR-0005)

## Date
2026-09-16

## Context
Between Milestone 1.0 and Milestone 1.21, the Agentic Substrate evolved its extraction and ingestion pipelines:
1. **PydanticAI Framework Overhead**: ADR-0003 originally introduced `PydanticAiGraphExtractor` utilizing `pydantic-ai` with `gemini-3.5-flash-lite`. ADR-0010 later introduced `DirectOpenRouterGraphExtractor` (using `meta-llama/llama-3.1-8b-instruct` via direct OpenRouter JSON completion), achieving sub-second extraction and 85% cost reduction. However, `pydantic-ai` remained in `pyproject.toml`, dragging in 67+ heavy transitive dependencies (OpenTelemetry, Google GenAI SDK, Google Auth, GRPC, logfire, etc.) into production container builds.
2. **Zombie Parsers & Chunkers**: `MarkdownParentChildChunker` was superseded by `StructureTolerantMarkdownChunker` (ADR-0004), and `MarkItDownDocumentParser` was superseded by `ParallelVlmDocumentParser` (Two-Pass Synthetic ToC with stateful rolling windows). They remained in the codebase as dead code tested only by legacy unit tests.
3. **Redundant Synthesizer Aliases**: `DeepSeekRagSynthesizer` and `GeminiRagSynthesizer` were superseded by `OpenRouterRagSynthesizer` (ADR-0007) running Google Gemma 4 (`google/gemma-4-26b-a4b-it`).
4. **Phantom Configuration in `.env` / `AppSettings`**: Settings for unbuilt features (e.g. S3 storage settings `S3_*`, `STORAGE_TYPE=s3`), never-forwarded variables (`OCR_TOC_BATCH_SIZE`), redundant prompts (`OCR_DEFAULT_MARKDOWN_PROMPT`), and phantom vector settings (`VECTOR_STORE_TYPE`) created operational confusion.

## Decision
1. **Prune `pydantic-ai` and Enforce Direct `openai` SDK**:
   - Remove `pydantic-ai>=2.31.0` from `pyproject.toml`.
   - Explicitly require `openai>=1.40.0` to maintain direct OpenRouter client support without transitive dependency coupling.
   - Core libraries `pydantic>=2.8.0` and `pydantic-settings>=2.4.0` are strictly preserved.
2. **Remove Deprecated Graph Extractors & Entity Catalogs**:
   - Delete `PydanticAiGraphExtractor`, `PydanticAiOpenRouterProviderFactory`, `ExistingEntityRegistry`, and `IEntityRegistry`.
   - Standardize all production graph extraction on `DirectOpenRouterGraphExtractor` with offline fallback to deterministic `StructuredPydanticGraphExtractor`.
3. **Remove Zombie Adapters & Chunkers**:
   - Delete `MarkdownParentChildChunker` (standardizing on `StructureTolerantMarkdownChunker`).
   - Delete `MarkItDownDocumentParser` (standardizing on `ParallelVlmDocumentParser` + `CompositeDocumentParser`).
   - Delete `DeepSeekRagSynthesizer` and `GeminiRagSynthesizer` (standardizing on `OpenRouterRagSynthesizer`).
4. **Harden Environment Configuration (`.env`, `.env.example`, `AppSettings`)**:
   - Remove `S3_*` and `STORAGE_TYPE` (the platform strictly implements `LocalFileSystemStorageAdapter` mounted in Docker/VM).
   - Remove `GEMINI_MODEL_NAME`, `GEMINI_MAX_RPM`, `GEMINI_MAX_TPM`, and `GEMINI_MAX_CONCURRENCY` (Gemini API is used exclusively for `models/gemini-embedding-2` via `GeminiEmbeddingAdapter`).
   - Remove `OCR_TOC_BATCH_SIZE` and `OCR_DEFAULT_MARKDOWN_PROMPT` (the parser defaults are managed internally).
   - Remove `VECTOR_STORE_TYPE` and `GRAPH_EXTRACTOR_PROVIDER`.

## Alternatives Considered

### Keeping PydanticAI as an Advisory Fallback
- **Pros**: Allows running with Gemini Flash without OpenRouter.
- **Cons**: Retains 67 heavy dependencies, bloats Docker image size by hundreds of megabytes, adds cognitive overhead for onboarding, and duplicates maintenance effort.
- **Rejected**: The deterministic `StructuredPydanticGraphExtractor` provides offline zero-cost testing, and `DirectOpenRouterGraphExtractor` provides superior throughput and reliability.

### Retaining S3 Settings for Future Use
- **Pros**: "In case someone needs S3 later".
- **Cons**: Keeping code/settings "just in case" is a classic anti-pattern (Hyrum's Law). No S3 adapter exists in `src/`, so these settings misled users into thinking S3 was operational.
- **Rejected**: Deprecate now; implement clean S3 adapters when actually required.

## Consequences
- **Build Performance**: 67 transitive packages removed, accelerating `uv sync` and Docker container build times.
- **Codebase Cleanliness**: Over 1.500 lines of dead code, obsolete test cases, and obsolete imports eliminated.
- **Strict Adherence**: 100% test pass rate (231 tests), 92% coverage, zero Ruff errors, and zero Mypy strict errors.
- **Documentation Parity**: Complete alignment between `README.md`, `CAPABILITY-MAP.md`, `.env.example`, and production runtime containers.
