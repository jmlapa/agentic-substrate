# Task List: Single-VM All-in-One Deployment (Marco 1.21)

> **Regra de ouro:** Implement → Test → Verify (passing) → Commit.
> Cada tarefa deve ter escopo atômico, critérios de aceitação testáveis e verificação explícita.

---

## Tasks

### Task 1: Criar templates de configuração e proxy (`deploy/vm/.env.example` e `deploy/vm/Caddyfile`)

**Description:** Cria o diretório `deploy/vm/` contendo o template de variáveis de ambiente com presets seguros para a VM e o `Caddyfile` configurado para roteamento unificado, SSL automático Let's Encrypt, compressão gzip/zstd e suporte a streaming de tokens.

**Acceptance criteria:**
- [x] `deploy/vm/.env.example` criado com presets para `POSTGRES_HOST=postgres`, `FALKORDB_HOST=falkordb`, `REDIS_HOST=redis`, `STORAGE_TYPE=local` e placeholders para `DOMAIN_NAME`, `ACME_EMAIL`, `POSTGRES_PASSWORD`, `OPENROUTER_API_KEY` e `GEMINI_API_KEY`.
- [x] `deploy/vm/Caddyfile` criado com suporte a variável `{$DOMAIN_NAME:localhost}`, roteamento de `/api/*` e `/docs*` para `api:8000`, e `/*` para `frontend:80`.
- [x] Headers `X-Forwarded-Proto` e `X-Real-IP` configurados no Caddy.

**Verification:**
```bash
test -f deploy/vm/.env.example && test -f deploy/vm/Caddyfile
grep "DOMAIN_NAME" deploy/vm/.env.example
grep "reverse_proxy api:8000" deploy/vm/Caddyfile
```

**Files touched:**
- `deploy/vm/.env.example`
- `deploy/vm/Caddyfile`

**Commit:** `feat(deploy): add env template and caddyfile for single-vm deployment`

---

### Task 2: Implementar a orquestração Docker Compose All-in-One (`deploy/vm/docker-compose.yml`)

**Description:** Cria o `deploy/vm/docker-compose.yml` que orquestra os 6 serviços: `caddy`, `api`, `frontend`, `postgres`, `falkordb` e `redis`. Todos em rede interna isolada `substrate_net`. Apenas as portas 80 e 443 do Caddy são mapeadas no host. Todos os bancos e backend possuem healthchecks e dependências estritas.

**Acceptance criteria:**
- [x] 6 serviços declarados: `caddy`, `frontend`, `api`, `postgres`, `falkordb`, `redis`.
- [x] Apenas o serviço `caddy` possui mapeamento de portas públicas (`80:80`, `443:443`).
- [x] `postgres`, `falkordb`, `redis`, `api` expõem portas apenas dentro da rede interna `substrate_net`.
- [x] Volumes de dados locais mapeados em `./data/postgres`, `./data/falkordb`, `./data/redis`, `./data/storage`, `./data/caddy_data`.
- [x] Healthchecks configurados para postgres, falkordb, redis e api com `depends_on: condition: service_healthy`.
- [x] `docker compose -f deploy/vm/docker-compose.yml config` valida com sucesso (com `.env` temporário).

**Verification:**
```bash
cp deploy/vm/.env.example deploy/vm/.env
docker compose -f deploy/vm/docker-compose.yml config > /dev/null
rm deploy/vm/.env
```

**Files touched:**
- `deploy/vm/docker-compose.yml`

**Commit:** `feat(deploy): add all-in-one docker compose orchestration for vm`

---

### Task 3: Implementar o script de setup e provisionamento (`deploy/vm/setup.sh`)

**Description:** Cria o script executável `deploy/vm/setup.sh` responsável por automatizar a inicialização do ambiente em uma VM Ubuntu/Debian recém-criada de forma totalmente idempotente.

**Acceptance criteria:**
- [x] Script verifica se Docker e Docker Compose v2 estão instalados (instala automaticamente se ausentes em distribuições Debian/Ubuntu).
- [x] Preserva `.env` existente (injetado via Terraform ou CI) ou gera a partir de `.env.example` com senha segura para PostgreSQL.
- [x] Cria os diretórios locais de persistência (`data/postgres`, `data/falkordb`, etc.) com permissões seguras.
- [x] Executa `docker compose pull` e `up -d --build`.
- [x] Executa migrações do Alembic (`exec api alembic upgrade head`).
- [x] Exibe status dos containers e URL de acesso.
- [x] Permissão de execução (`chmod +x`).

**Verification:**
```bash
bash -n deploy/vm/setup.sh
test -x deploy/vm/setup.sh
```

**Files touched:**
- `deploy/vm/setup.sh`

**Commit:** `feat(deploy): add automated idempotent setup script for vm appliance`

---

### Task 4: Implementar testes automatizados de configuração (`tests/unit/test_deploy_vm_configuration.py`)

**Description:** Adiciona testes unitários com pytest para validar a integridade estática de todos os arquivos de configuração do módulo de deploy, garantindo que portas sensíveis não sejam expostas, que variáveis essenciais estejam presentes e que o script de setup seja sintaticamente válido.

**Acceptance criteria:**
- [x] Teste valida que `deploy/vm/docker-compose.yml` não faz binding de portas para o host nos serviços `postgres`, `falkordb`, `redis` e `api`.
- [x] Teste valida que todos os 6 serviços possuem healthchecks ou dependências saudáveis.
- [x] Teste valida que `deploy/vm/Caddyfile` contém blocos de proxy para `/api/*` e `/*`.
- [x] Teste valida que as variáveis do `.env.example` cobrem as configurações do `AppSettings`.
- [x] Teste valida a sintaxe bash do `setup.sh` usando `bash -n`.
- [x] 100% dos testes passam com `pytest`.

**Verification:**
```bash
uv run pytest tests/unit/test_deploy_vm_configuration.py -v
```

**Files touched:**
- `tests/unit/test_deploy_vm_configuration.py`

**Commit:** `test(deploy): add automated configuration and security validation suite for vm deploy`

---

### Task 5: Documentar deploy em VM no README.md e executar gate de qualidade

**Description:** Atualiza a documentação principal no `README.md` incluindo a seção "Deploy em Cloud Própria (VM Única)" com passos rápidos e claros, e executa a verificação completa de qualidade pré-commit.

**Acceptance criteria:**
- [x] `README.md` atualizado com seção dedicada ao deploy em VM única (AWS EC2, GCP Compute Engine).
- [x] Instruções cobrem tanto o provisionamento automatizado quanto manual.
- [x] `make pre-commit` executado e passando com 100% de sucesso (Ruff, Mypy strict, Pytest com cobertura).

**Verification:**
```bash
make pre-commit
```

**Files touched:**
- `README.md`
- `CAPABILITY-MAP.md` (se necessário ajuste final de status)

**Commit:** `docs(deploy): document single-vm deployment in readme and pass quality gates`
