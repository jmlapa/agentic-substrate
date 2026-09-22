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
                      │  (FastAPI REST + Streamable SSE MCP)   │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │            Knowledge Module            │
                      │  ┌──────────────────────────────────┐  │
                      │  │ Ingestion Saga (Event-Driven)    │  │
                      │  │ ├─ Parallel VLM & Multi. Parser  │  │
                      │  │ ├─ Structure-Tolerant Chunker    │  │
                      │  │ ├─ Gemini Embedding 2 (768d MRL) │  │
                      │  │ └─ Direct OpenRouter Extractor   │  │
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

### 2. Direct OpenRouter Graph Extraction & Rate Limiting (Llama 3.1 8B)
- **Zero-Hallucination JSON Completion**: Extracts ontological entities and relationships using `meta-llama/llama-3.1-8b-instruct` directly through OpenRouter's structured output API.
- **Referential Integrity Filtering**: Enforces strict ontological domain matching and self-referential cycle elimination in memory before graph persistence.
- **High-Throughput Token Bucket Limiter**: Transport-level token bucket rate limiter sustaining 1.500 RPM / 10.000.000 TPM with sliding window tracking.
- **Deterministic Fallback Engine**: Built-in local fallback extractor ensuring 100% ingestion resilience even in disconnected or zero-token environments.

### 3. Universal Structure-Tolerant Markdown Chunker
- **`AtomicBlockLexer`**: Classifies Markdown into atomic units (`CODE_BLOCK`, `TABLE`, `LIST_ITEM`, `HEADING`, `PARAGRAPH`).
- **Zero-Damage Chunking**: Never splits tables or code blocks across chunk boundaries.
- **Hierarchical Breadcrumbs**: Preserves complete section hierarchy in Parent Chunks (~1.200 tokens) and Child Chunks (~200 tokens + 30 overlap).

### 4. Parallel VLM & Multimodal Document Parser
- **Fast-Path Zero-Cost Default**: Plaintext and digital PDFs execute natively on CPU with zero LLM API calls and sub-second parsing speed.
- **Resilient Parallel Two-Pass OCR**: Scanned documents, complex diagrams, and tables leverage `qwen/qwen3-vl-32b-instruct` with stateful rolling-window Two-Pass Synthetic ToC extraction.
- **Inter-Page Continuity & Normalization**: Automatically stitches broken tables, headers, and code blocks across page boundaries.

### 5. Fact-Dense RAG Synthesis with Google Gemma 4
- **Dual-Mode Architecture**: Supports both full RAG synthesis with evidence citations and raw candidate retrieval modes.
- **Fact-Dense Synthesis**: Powered by `google/gemma-4-26b-a4b-it` via OpenRouter, delivering high-density synthesis while defending against prompt injection via XML boundary isolation.
- **Dynamic Token Budgeting**: Enforces a strict 32k context token budget with bounded multiplicative graph decay and natural seed deduplication.

### 6. Frontend Console SPA (`/frontend`)
- Modern, responsive SPA built with **React 18.3 + Vite 5.4 + TypeScript 5.5 + Tailwind CSS 3.4** and TanStack React Query v5.
- Visual management of Ontologies, Knowledge Bases, live ingestion pipeline progress tracker, and interactive RAG Playground with synthesized LLM responses and evidence inspection.

### 7. Streamable HTTP/SSE Model Context Protocol (MCP) Server
- **Unified Edge Protocol**: Standardized Anthropic MCP interface hosted over HTTP/SSE at `/mcp/sse` and `/mcp/messages`.
- **In-Process High Performance**: Direct in-memory invocation of use cases via `AppContainer` with 0ms extra IPC latency.
- **Autonomous Agent Interoperability**: Seamlessly connect Cursor, Claude Desktop, LangGraph, CrewAI, AutoGen, or custom agents.
- **Cognitive Tools**:
  - `knowledge_query`: Hybrid GraphRAG query with fact-dense synthesis and optional graph triples evidence.
  - `knowledge_list_kbs`: Lists all available Knowledge Bases with status and document counts.
  - `knowledge_search_notes`: Fast-path instant lexical and structural header search without LLM token cost.

### 8. Google Drive Folder Data Sources & Blue/Green Ingestion
- **Automated Continuous Synchronization**: Ingest entire Google Drive folders with delta detection and recursive subfolder traversal.
- **Enterprise-Grade Blue/Green Ingestion**: Ingests changed files into an isolated Green partition; once all files are successfully chunked, embedded, and mapped to the graph, an atomic swap promotes the new version with zero search downtime.
- **Secure Service Account Integration**: Private RSA keys stay protected on the VM disk (`GOOGLE_APPLICATION_CREDENTIALS`). End users never upload credentials in the browser; they simply share target Google Drive folders with the Service Account email.
- **Frontend Management**: Dedicated UI for configuring connectors, monitoring live execution runs, and inspecting granular file failure summaries.

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

## ☁️ Single-VM All-in-One Cloud Deployment

You can deploy the entire Agentic Substrate stack (Frontend SPA, FastAPI Backend, PostgreSQL 16 with pgvector, FalkorDB, and Redis) to your own cloud VM (AWS EC2 `t4g.medium`/`t3.medium`, GCP Compute Engine `e2-standard-2`, Hetzner, or DigitalOcean) in **1 command** with automated Let's Encrypt SSL/TLS via Caddy.

### Recommended VM Specifications
- **OS**: Ubuntu 22.04 LTS or 24.04 LTS (x86_64 or arm64)
- **Memory**: 8 GB RAM (recommended to support high-concurrency PDF ingestion and HNSW vector indexing without OOM)
- **Disk**: 50 GB SSD persistent block storage
- **Firewall / Security Group**: Expose only ports `80` (HTTP) and `443` (HTTPS) to the public internet. Database ports (`5432`, `6379`, `6380`) and API (`8000`) remain strictly internal.

### 1-Command Automated Deploy (SSH)
```bash
# 1. Clone the repository on your VM
git clone https://github.com/insider/agentic-substrate.git /opt/agentic-substrate
cd /opt/agentic-substrate

# 2. Configure your public domain and secrets
cp deploy/vm/.env.example deploy/vm/.env
# Edit deploy/vm/.env: set DOMAIN_NAME (e.g. staging.yourdomain.com), ACME_EMAIL, OPENROUTER_API_KEY / GEMINI_API_KEY
nano deploy/vm/.env

# 3. Run the automated setup
bash deploy/vm/setup.sh
```

The script will automatically install Docker & Compose v2 (if missing), configure data storage with proper permissions, launch all 6 services, and run database migrations.

### Automated Provisioning via Terraform / Cloud-Init
If you manage your VMs with Terraform, OpenTofu, or cloud-init, pass your `.env` directly via `user_data` and trigger `bash deploy/vm/setup.sh` at the end of the script for fully automated, zero-touch deployment:
```hcl
# Example Terraform user_data snippet:
resource "aws_instance" "substrate_vm" {
  # ...
  user_data = <<-EOF
    #!/bin/bash
    git clone https://github.com/insider/agentic-substrate.git /opt/agentic-substrate
    cat <<'ENV' > /opt/agentic-substrate/deploy/vm/.env
    DOMAIN_NAME="staging.yourdomain.com"
    ACME_EMAIL="devops@yourdomain.com"
    OPENROUTER_API_KEY="${var.openrouter_api_key}"
    GEMINI_API_KEY="${var.gemini_api_key}"
    GOOGLE_APPLICATION_CREDENTIALS="/app/credentials/google-service-account.json"
    ENV
    cd /opt/agentic-substrate && bash deploy/vm/setup.sh
  EOF
}
```

### Google Drive Connector Deployment (Service Account Key)
When deploying to a VM, Google Drive folder synchronization requires a **GCP Service Account JSON key** placed on the VM disk and mounted into the backend API container:

1. **Create Service Account in GCP Console**:
   - In your Google Cloud Project, enable the **Google Drive API**.
   - Create a Service Account (e.g. `agentic-substrate-drive@<project-id>.iam.gserviceaccount.com`).
   - Create and download a new private key in JSON format.
2. **Copy the JSON key to the VM Disk**:
   - Save the key file on your VM host inside `deploy/vm/credentials/`:
     ```bash
     mkdir -p deploy/vm/credentials
     cp /path/to/downloaded-key.json deploy/vm/credentials/google-service-account.json
     chmod 600 deploy/vm/credentials/google-service-account.json
     ```
   - *Note:* The `deploy/vm/credentials/` directory is automatically mounted read-only into `/app/credentials` inside the API container via Docker Compose.
3. **Configure the Environment Variable**:
   - In `deploy/vm/.env`, set:
     ```bash
     GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-service-account.json
     ```
4. **Share Target Folders in Google Drive**:
   - Open any folder in Google Drive you wish to index.
   - Click **Share (Compartilhar)** and add your Service Account email (`agentic-substrate-drive@...`) with **Viewer (Leitor)** permission.
   - In the frontend console (`/knowledge-bases/<kbId>`), paste the Folder ID or full Drive URL to trigger synchronization!

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

### Connect Autonomous Agents via Model Context Protocol (MCP)
External agents can connect directly to the Streamable HTTP/SSE MCP endpoint (`http://localhost:8000/mcp/sse` or `https://<your-domain>/mcp/sse`).

**Claude Desktop / Cursor Configuration (`mcpServers`):**
```json
{
  "mcpServers": {
    "agentic-substrate": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

**Python Client Example (`mcp` SDK):**
```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


async def main():
    async with sse_client("http://localhost:8000/mcp/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print([t.name for t in tools.tools])

            # Query Knowledge Graph
            result = await session.call_tool(
                "knowledge_query",
                arguments={"kb_id": "<kb-uuid>", "query": "Quais são as regras de tributação?"},
            )
            print(result.content[0].text)


asyncio.run(main())
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
│   │   ├── 0005-configurable-ocr-and-openrouter-vlm.md
│   │   ├── ...
│   │   ├── 0010-lean-7b-direct-openrouter-structured-extractor.md
│   │   └── 0011-deprecation-of-pydantic-ai-legacy-parsers-and-env-hardening.md
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
- [ADR-0003: PydanticAI v2 Graph Extraction, Rate Limiting and Cumulative Canonization](docs/decisions/0003-pydantic-ai-graph-extractor-and-rate-limiter.md) *(Superseded by ADR-0010 & ADR-0011)*
- [ADR-0004: Universal Structure-Tolerant Markdown Chunker](docs/decisions/0004-universal-structure-tolerant-chunker.md)
- [ADR-0005: Configurable Multimodal OCR, OpenRouter VLM and PydanticAI OpenAI Provider](docs/decisions/0005-configurable-ocr-and-openrouter-vlm.md)
- [ADR-0006: CQRS Consolidated Read Model Projections and O(1) Relational Query Engine](docs/decisions/0006-cqrs-read-model-projections.md)
- [ADR-0007: OpenRouter Gemma 4 Fact-Dense RAG Synthesis & Dual-Mode Query Architecture](docs/decisions/0007-openrouter-gemma-4-fact-dense-rag-synthesis.md)
- [ADR-0008: Optimized GraphRAG Retrieval, Candidate Fusion & Dynamic Token Budgeting](docs/decisions/0008-optimized-graphrag-retrieval-and-budgeting.md)
- [ADR-0009: Bounded Multiplicative Graph Decay, Natural Candidate Deduplication & Asymmetric Retrieval](docs/decisions/0009-bounded-multiplicative-graph-decay-and-natural-deduplication.md)
- [ADR-0010: Lean 7B/8B Structured Ontology Extractor via Direct OpenRouter JSON Completion](docs/decisions/0010-lean-7b-direct-openrouter-structured-extractor.md)
- [ADR-0011: Deprecation of PydanticAI, Legacy Parsers/Chunkers, and Environment Hardening](docs/decisions/0011-deprecation-of-pydantic-ai-legacy-parsers-and-env-hardening.md)
- [ADR-0012: Streamable HTTP/SSE Model Context Protocol (MCP) Server and Modular Tool Providers](docs/decisions/0012-streamable-http-sse-mcp-server.md)

---

## ⚖️ License
MIT License. Created for the **Agentic Substrate** initiative.

