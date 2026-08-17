# Spec: Local Infrastructure & Development Environment

## 1. Objective
Establish a reproducible, single-command local infrastructure utilizing Docker Compose (PostgreSQL 16 + pgvector, FalkorDB, Redis) and a fully configured local `.env` environment file. This enables developers and automated integration suites to execute real database migrations (`make migrate`), persistent event sourcing, vector search, graph storage, and local file storage without external cloud dependencies.

## 2. Tech Stack & Dependencies
- **PostgreSQL 16 with pgvector**: `pgvector/pgvector:0.8.6-pg16`
- **FalkorDB**: `falkordb/falkordb:v4.20.3-alpine`
- **Redis**: `redis:7.4.10-alpine`
- **Configuration Engine**: `pydantic-settings` via `AppSettings`
- **Migration Engine**: `Alembic` + `asyncpg`

## 3. Commands
```bash
# Start local infrastructure in detached mode
make dev
# (or: docker compose -f docker/docker-compose.yml up -d)

# Stop local infrastructure
make dev-down
# (or: docker compose -f docker/docker-compose.yml down)

# Check container status and health
docker compose -f docker/docker-compose.yml ps

# Execute database migrations
make migrate

# Full quality gate verification
make pre-commit
```

## 4. Project Structure
```
docker/
  docker-compose.yml   → Docker Compose orchestration for postgres, falkordb, redis
.env.example           → Version-controlled template
.env                   → Local development environment configuration (git-ignored)
data/                  → Git-ignored directory for volumes and local storage
  postgres/            → Persistent PostgreSQL data
  falkordb/            → Persistent FalkorDB data
  redis/               → Persistent Redis data
  storage/             → Local file object storage
```

## 5. Code Style & Alignment
Compose service definitions must match `AppSettings` default values:
- PostgreSQL: `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`, `POSTGRES_DB=agentic_substrate`, Port `5432:5432`.
- FalkorDB: Port `6380:6379`.
- Redis: Port `6379:6379`.
- Healthchecks on all services with sensible interval/timeout parameters.

## 6. Testing Strategy
1. **Container Health & Connectivity**: Verify containers start and pass internal healthchecks.
2. **Schema & Migration Verification**: Execute `alembic upgrade head` (`make migrate`) to verify tables and vector extension creation.
3. **Configuration Parsing**: Ensure `AppSettings()` initializes cleanly from `.env`.
4. **Quality Gates**: Ensure `make pre-commit` passes without errors.

## 7. Boundaries
- **Always**: Keep `.env` and `data/` ignored in git (`.gitignore`); maintain aligned default credentials across `.env.example`, `docker-compose.yml`, and `AppSettings`.
- **Ask first**: Changing public network ports or replacing container base images.
- **Never**: Hardcode sensitive secrets or commit real `.env` files to git.

## 8. Success Criteria
- `docker/docker-compose.yml` updated with aligned development credentials (`postgres`/`postgres`/`agentic_substrate`), volume mounts under `../data/`, and healthchecks.
- `.env` generated from `.env.example` with local development presets.
- `SPEC-local-infrastructure.md`, `tasks/plan.md`, and `tasks/todo.md` created and synchronized.
- Git status confirms `.env` is untracked and ignored.
- Quality gates pass (`make pre-commit`).
