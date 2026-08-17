# ADR-0004: Universal Structure-Tolerant Markdown Chunker

## Status
Accepted

## Date
2026-08-17

## Context
Standard recursive text splitters (e.g. LangChain, LlamaIndex) split on arbitrary character counts or regex delimiters, which often:
- Fractures Markdown tables across chunks, destroying tabular syntax.
- Splits fenced code blocks, leaving invalid syntax snippets.
- Destroys structural context headers and breadcrumb hierarchy.
- Fails completely on unstructured Markdown files that lack explicit `# Header` hierarchies (e.g. raw OCR texts, legal codes).

## Decision
Implement the **`StructureTolerantMarkdownChunker`** utilizing an **`AtomicBlockLexer`**:
1. **Atomic Block Lexing**: Classifies text into atomic blocks (`CODE_BLOCK`, `TABLE`, `LIST_ITEM`, `HEADING`, `PARAGRAPH`, `LINE_BREAK`). Atomic blocks like tables and code blocks are never broken up internally.
2. **Hierarchical Breadcrumbs**: Tracks header depths (`#`, `##`, `###`) and propagates contextual paths to parent chunks.
3. **Token Budget Packing**: Aggregates atomic blocks into Parent Chunks (~1.200 tokens) with greedy bin packing, falling back gracefully to sub-splitting oversized paragraphs while preserving atomic blocks.
4. **Child Chunks with Overlap**: Generates compact Child Chunks (~200 tokens + 30 overlap) linked by UUID to their Parent Chunk.

## Alternatives Considered

### Fixed-Size Sliding Window Character Chunking
- **Pros**: Trivial implementation.
- **Cons**: Severe loss of tabular and code semantics; ungrounded retrieval results.
- **Rejected**: Inadequate for high-precision legal, technical, and regulatory documents.

## Consequences
- 100% preservation of Markdown tables and code snippets during ingestion.
- Universal support for both heavily structured and completely unstructured Markdown documents.
