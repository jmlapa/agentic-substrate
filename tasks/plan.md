# Implementation Plan: Local Infrastructure & Development Environment

## Context & Problem
We need a standardized local infrastructure setup using Docker Compose and a real `.env` file so that developers can run the entire substrate (PostgreSQL 16 with pgvector, FalkorDB, Redis, and local object storage) with one command, apply database migrations with `make migrate`, and verify end-to-end functionality locally.

---

## Proposed Architecture & Workflow

1. **Docker Compose Harmonization (`docker/docker-compose.yml`)**:
   - Pin deterministic image versions instead of floating/latest tags:
     - `pgvector/pgvector:0.8.0-pg16`
     - `falkordb/falkordb:v0.4.0`
     - `redis:7.2.4-alpine`
   - Align PostgreSQL credentials to standard development defaults (`POSTGRES_USER: postgres`, `POSTGRES_PASSWORD: postgres`, `POSTGRES_DB: agentic_substrate`).
   - Retain port mappings (`5432` for postgres, `6380:6379` for falkordb, `6379:6379` for redis).
   - Ensure data volume directories mount into `../data/postgres`, `../data/falkordb`, `../data/redis`.
   - Ensure healthchecks are configured for each service.

2. **Local Environment Configuration (`.env`)**:
   - Create the active `.env` file based on `.env.example`.
   - Set development defaults (`ENVIRONMENT=development`, `DEBUG=true`, `POSTGRES_*`, `FALKORDB_*`, `STORAGE_LOCAL_BASE_DIR=./data/storage`).
   - Verify that `.gitignore` prevents `.env` and `data/` from being tracked.

3. **Makefile Integration & Verification Checkpoints**:
   - Verify `make dev` starts the containers.
   - Verify `make dev-down` stops the containers.
   - Verify `make migrate` applies Alembic migrations against the local PostgreSQL container.
   - Execute `make pre-commit` for full quality gate compliance.

---

## Phase Breakdown

### Phase 1: Harmonize `docker/docker-compose.yml`
- Update credentials and database names in `docker/docker-compose.yml` to match `AppSettings` defaults (`postgres`/`postgres`/`agentic_substrate`).
- Verify container names and healthcheck definitions.

### Phase 2: Create Local `.env` & Storage Directory Structure
- Create `.env` from `.env.example` configured for local development.
- Ensure local directory structure `data/storage` is initialized.
- Verify that `git status` ignores `.env` and `data/`.

### Phase 3: Verification & Quality Gate
- Validate that `AppSettings` correctly loads and parses values from the created `.env`.
- Run `make pre-commit` (Ruff formatting, Ruff linting, Mypy strict, Pytest).
