# Tasks: Local Infrastructure & Development Environment

- [ ] Task 1: Harmonize `docker/docker-compose.yml`
  - Acceptance: Pinned container image versions (`pgvector/pgvector:0.8.0-pg16`, `falkordb/falkordb:v0.4.0`, `redis:7.2.4-alpine`), service credentials match `AppSettings` defaults (`postgres`/`postgres`/`agentic_substrate`), volume directories point to `../data/*`, healthchecks configured.
  - Verify: Validate yaml syntax and verify container declarations.
  - Files: `docker/docker-compose.yml`

- [ ] Task 2: Create Local `.env` and Directory Setup
  - Acceptance: Local `.env` file generated with development configuration, `data/storage` directory exists, git ignores `.env` and `data/`.
  - Verify: Run `git status` to ensure `.env` and `data/` are not tracked.
  - Files: `.env`

- [ ] Task 3: Verification & Quality Gates
  - Acceptance: `AppSettings` loads `.env` accurately; full test suite and quality gates pass.
  - Verify: `make pre-commit` passes with 0 errors.
  - Files: `tasks/todo.md`, `CHANGELOG.md`
