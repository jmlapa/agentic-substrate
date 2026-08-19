# Agentic Substrate

> **A high-performance, modular, and event-sourced substrate for autonomous AI agents and hybrid GraphRAG systems.**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Mypy Strict](https://img.shields.io/badge/mypy-strict-brightgreen.svg)](https://mypy.readthedocs.io/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Test Coverage](https://img.shields.io/badge/coverage-93%25-green.svg)](https://pytest.org/)

---

## 🏛️ Architecture Overview

The **Agentic Substrate** is built on **Hexagonal Architecture (Ports & Adapters)**, **Domain-Driven Design (DDD)**, and **Event Sourcing**, adhering to the strict **Single Class per File** discipline.

```
                      ┌────────────────────────────────────────┐
                      │              API Gateway               │
                      │     (FastAPI REST / OpenAPI DTOs)      │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │            Knowledge Module            │
                      │  ┌──────────────────────────────────┐  │
                      │  │ Ingestion Saga (Event-Driven)    │  │
                      │  │ ├─ MarkItDown Parser (PDF/DOCX)  │  │
                      │  │ ├─ Structure-Tolerant Chunker    │  │
                      │  │ ├─ Gemini Embedding 2 (768d MRL) │  │
                      │  │ └─ PydanticAI v2 Graph Extractor │  │
                      │  └──────────────────────────────────┘  │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │              Kernel Core               │
                      │  (Aggregates, Events, Event Store, Bus)│
                      └───────────────────┬────────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
       ┌─────────────────────────┐                 ┌─────────────────────────┐
       │   PostgreSQL 16 + Async │                 │    Unified FalkorDB     │
       │    (Event Sourcing &    │                 │ (Vector HNSW + Property │
       │    Optimistic Locking)  │                 │    Graph Dual-Store)    │
       └─────────────────────────┘                 └─────────────────────────┘
```

---

## ⚡ Key Capabilities

### 1. Unified FalkorDB Hybrid GraphRAG
- Single database engine for both vector retrieval and property graph traversals.
- **Structural Document Graph**: `(:Document)-[:HAS_PARENT]->(:ParentChunk)-[:HAS_CHILD]->(:ChildChunk)`.
- **Native HNSW Vector Index**: Embedded directly on `(:ChildChunk.embedding)` (768d cosine similarity).
- **Conceptual Mentions**: Links Parent Chunks to ontological entities: `(:ParentChunk)-[:MENTIONS]->(:Entity)`.
- **Single-Hop OpenCypher Retrieval**: Queries vector similarities with `db.idx.vector.queryNodes` and ascends to Parent context and entity subgraphs in sub-10ms queries.

### 2. PydanticAI v2 Dynamic Graph Extraction & Rate Limiting
- **Zero-Hallucination Extraction**: Compiles dynamic Pydantic models in runtime from user-defined ontologies.
- **Transport-Level Rate Limiter (`RateLimitedAsyncTransport`)**: Intercepts HTTP calls with a sliding window token-bucket limiter (300 RPM / 1.000.000 TPM for `gemini-3.5-flash-lite`).
- **Cumulative Entity Canonization (`ExistingEntityRegistry`)**: Injects existing extracted entities into extraction prompts per Knowledge Base to avoid duplicate graph nodes.
- **Concurrent Batching**: Parallelizes Parent Chunk extraction via `asyncio.gather` with concurrency semaphores (`max_concurrency=15`).

### 3. Universal Structure-Tolerant Markdown Chunker
- **`AtomicBlockLexer`**: Classifies Markdown into atomic units (`CODE_BLOCK`, `TABLE`, `LIST_ITEM`, `HEADING`, `PARAGRAPH`).
- **Zero-Damage Chunking**: Never splits tables or code blocks across chunk boundaries.
- **Hierarchical Breadcrumbs**: Preserves complete section hierarchy in Parent Chunks (~1.200 tokens) and Child Chunks (~200 tokens + 30 overlap).

### 4. Configurable Multimodal OCR & OpenRouter Vision (`MarkItDown`)
- **Fast-Path Zero-Cost Default**: Plaintext and text-layer documents execute natively on CPU with zero LLM API calls and sub-second parsing speed.
- **Multimodal Visual Analysis**: Optional toggle routing image-heavy, diagrammatic, and scanned documents to `qwen/qwen3-vl-30b-a3b-instruct` via OpenRouter.
- **Custom Markdown Structure Injection**: Dynamic instruction prompt customizing Markdown formatting (strict tables, mathematical preservation, diagram annotations).

### 5. Frontend Console SPA (`/frontend`)
- Modern, responsive SPA built with **React 18.3 + Vite 5.4 + TypeScript 5.5 + Tailwind CSS 3.4** and TanStack React Query v5.
- Visual management of Ontologies, Knowledge Bases, live ingestion pipeline progress tracker, and interactive RAG Playground with synthesized LLM responses and evidence inspection.

---

## 🚀 Quick Start

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/)
- [Python 3.13+](https://www.python.org/)
- [`uv`](https://docs.astral.sh/uv/) package manager
- [Node.js 20+](https://nodejs.org/) (for frontend console)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/insider/agentic-substrate.git
cd agentic-substrate
uv sync
cd frontend && npm install && cd ..
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and configure your OPENROUTER_API_KEY and GEMINI_API_KEY
```

### 3. Start Local Infrastructure
```bash
make dev
```
This spins up:
- **PostgreSQL 16** on `localhost:5432` (`substrate_postgres`)
- **FalkorDB Graph Store** on `localhost:6380` (`substrate_falkordb`)
- **Redis Cache** on `localhost:6379` (`substrate_redis`)

### 4. Run Database Migrations
```bash
make migrate
```

### 5. Run Quality Verification Gate
```bash
make pre-commit
```

### 6. Start the API Server & Frontend Console
```bash
# Terminal 1: Backend API
make run

# Terminal 2: Frontend Console SPA
cd frontend && npm run dev
```
- Interactive OpenAPI Swagger docs: `http://localhost:8000/docs`
- Frontend Console SPA: `http://localhost:3000`

---

## 🧪 Ingestion & Query CLI

### Ingest a Document into GraphRAG
You can ingest any PDF, Markdown, or text file directly into the Brazilian Legal Ontology or custom ontologies:
```bash
uv run python scripts/ingest_document.py "/path/to/document.pdf"
```

### Execute a Hybrid GraphRAG Query
```bash
curl -X POST http://localhost:8000/api/v1/knowledge/bases/{kb_id}/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quais são as competências privativas do Presidente da República?",
    "top_k": 3
  }'
```

---

## 📁 Repository Structure

```
agentic-substrate/
├── AGENTS.md                   # Inviolable agent rules & architecture standards
├── CAPABILITY-MAP.md           # Module dependency & capability map
├── CHANGELOG.md                # Semantic versioning changelog
├── Makefile                    # Quality gates & orchestration commands
├── docs/
│   ├── decisions/              # Architecture Decision Records (ADRs)
│   │   ├── 0001-hexagonal-event-sourced-architecture.md
│   │   ├── 0002-unified-falkordb-hybrid-graphrag.md
│   │   ├── 0003-pydantic-ai-graph-extractor-and-rate-limiter.md
│   │   ├── 0004-universal-structure-tolerant-chunker.md
│   │   └── 0005-configurable-ocr-and-openrouter-vlm.md
│   └── ideas/                  # Concept exploration documents
├── frontend/                   # React 18 + Vite SPA Console Hub & Playground
├── migrations/                 # Alembic async database migrations
├── scripts/                    # CLI scripts (ingestion, ontologies)
│   ├── ingest_document.py
│   └── register_legal_ontology.py
├── src/
│   ├── api_gateway/            # FastAPI routes, DTOs & IoC Container
│   ├── kernel/                 # Pure domain primitives, Event Store & Bus
│   └── modules/
│       └── knowledge/          # GraphRAG domain, sagas, adapters & chunkers
└── tests/                      # Unit & integration tests (92%+ coverage)
```

---

## 🛠️ Developer Commands

| Command | Description |
|---|---|
| `make pre-commit` | **Official Quality Gate**: Runs linter, formatter, type checker, and tests. |
| `make test` | Run full Pytest suite with code coverage. |
| `make lint` | Run Ruff linter. |
| `make format` | Format code with Ruff. |
| `make typecheck` | Run Mypy in strict mode (`--strict`). |
| `make dev` | Start local Docker infrastructure containers. |
| `make dev-down` | Stop local Docker containers. |
| `make migrate` | Apply all pending database migrations. |
| `make run` | Start FastAPI development server with hot-reload. |

---

## 📜 Architectural Decisions (ADRs)
- [ADR-0001: Hexagonal Event-Sourced Architecture with Single Class Per File](docs/decisions/0001-hexagonal-event-sourced-architecture.md)
- [ADR-0002: Unified FalkorDB Hybrid GraphRAG Engine](docs/decisions/0002-unified-falkordb-hybrid-graphrag.md)
- [ADR-0003: PydanticAI v2 Graph Extraction, Rate Limiting and Cumulative Canonization](docs/decisions/0003-pydantic-ai-graph-extractor-and-rate-limiter.md)
- [ADR-0004: Universal Structure-Tolerant Markdown Chunker](docs/decisions/0004-universal-structure-tolerant-chunker.md)
- [ADR-0005: Configurable Multimodal OCR, OpenRouter VLM and PydanticAI OpenAI Provider](docs/decisions/0005-configurable-ocr-and-openrouter-vlm.md)
- [ADR-0006: CQRS Consolidated Read Model Projections and O(1) Relational Query Engine](docs/decisions/0006-cqrs-read-model-projections.md)
- [ADR-0007: OpenRouter Gemma 4 Fact-Dense RAG Synthesis & Dual-Mode Query Architecture](docs/decisions/0007-openrouter-gemma-4-fact-dense-rag-synthesis.md)
- [ADR-0008: Optimized GraphRAG Retrieval, Candidate Fusion & Dynamic Token Budgeting](docs/decisions/0008-optimized-graphrag-retrieval-and-budgeting.md)

---

## ⚖️ License
MIT License. Created for the **Agentic Substrate** initiative.

