# Tasks: Modular Caddy Environment Rules & Zero-Conflict VM Deployment (Marco 1.23)

## Task List

- [x] `task-1`: Atualizar `Caddyfile` e `docker-compose.yml` para suporte a regras modulares
- [x] `task-2`: Criar estrutura `deploy/vm/rules/` com `.gitkeep`, `README.md` e `auth.caddy.example`
- [x] `task-3`: Atualizar `.gitignore`, `setup.sh` e `.env.example` com isolamento de ambiente
- [x] **Checkpoint 1 (Foundation & Isolation):** Validar integridade dos arquivos e isolamento git
- [x] `task-4`: Validar sintaxe do Caddyfile e testar backward compatibility
- [x] `task-5`: Registrar v0.8.1 no `CHANGELOG.md` e preparar fluxo de subtree push
- [x] **Checkpoint 2 (Final Verification):** Árvore limpa e pronto para subtree push upstream

---

### Task Details

#### Task 1: Atualizar `Caddyfile` e `docker-compose.yml`
**Description:** Adiciona `import /etc/caddy/rules/*.caddy` no bloco de site do `Caddyfile` e adiciona o volume `./rules:/etc/caddy/rules:ro` no serviço `caddy` em `docker-compose.yml`.
**Dependencies:** None
**Estimated scope:** S (2 files)
**Acceptance Criteria:**
- `deploy/vm/Caddyfile` contém `import /etc/caddy/rules/*.caddy` no início do site block.
- `deploy/vm/docker-compose.yml` monta `./rules:/etc/caddy/rules:ro` no serviço `caddy`.
**Verification:**
- [ ] `grep "import /etc/caddy/rules/\*.caddy" substrate/deploy/vm/Caddyfile`
- [ ] `grep "./rules:/etc/caddy/rules:ro" substrate/deploy/vm/docker-compose.yml`
**Files:**
- `substrate/deploy/vm/Caddyfile`
- `substrate/deploy/vm/docker-compose.yml`

---

#### Task 2: Criar estrutura `deploy/vm/rules/`
**Description:** Cria o diretório `deploy/vm/rules/` com `.gitkeep`, `README.md` explicativo e template `auth.caddy.example`.
**Dependencies:** `task-1`
**Estimated scope:** S (3 files)
**Acceptance Criteria:**
- `deploy/vm/rules/.gitkeep` garante persistência do diretório no Git.
- `deploy/vm/rules/auth.caddy.example` documenta configuração de basic_auth e comando `caddy hash-password`.
- `deploy/vm/rules/README.md` explica como estender o Caddyfile de forma desacoplada.
**Verification:**
- [ ] `ls -la substrate/deploy/vm/rules/`
**Files:**
- `substrate/deploy/vm/rules/.gitkeep`
- `substrate/deploy/vm/rules/README.md`
- `substrate/deploy/vm/rules/auth.caddy.example`

---

#### Task 3: Atualizar `.gitignore`, `setup.sh` e `.env.example`
**Description:** Ignora `rules/*.caddy` no `.gitignore`, adiciona criação de `rules/` no `setup.sh` e documenta `DOMAIN_NAME=:80` no `.env.example`.
**Dependencies:** `task-2`
**Estimated scope:** M (4 files)
**Acceptance Criteria:**
- `.gitignore` (do substrate e da raiz) ignora `deploy/vm/rules/*.caddy` preservando `.example`.
- `setup.sh` executa `mkdir -p "${SCRIPT_DIR}/rules"`.
- `.env.example` documenta `DOMAIN_NAME=:80` para acessos diretos via IP em staging.
**Verification:**
- [ ] `grep "rules/\*.caddy" substrate/.gitignore`
- [ ] `grep 'mkdir -p "${SCRIPT_DIR}/rules"' substrate/deploy/vm/setup.sh`
- [ ] `grep -A 2 "DOMAIN_NAME" substrate/deploy/vm/.env.example`
**Files:**
- `substrate/.gitignore`
- `.gitignore`
- `substrate/deploy/vm/setup.sh`
- `substrate/deploy/vm/.env.example`

---

### Checkpoint 1 (Foundation & Isolation)
- [ ] Todas as regras de infraestrutura base e diretórios criados
- [ ] Teste de isolamento Git: criar arquivo `.caddy` temporário e validar `git status --porcelain` vazio
- [ ] Revisão dos arquivos antes de avançar

---

#### Task 4: Validar sintaxe e testar backward compatibility
**Description:** Testa se o `Caddyfile` continua válido com e sem regras em `rules/`, preservando todas as rotas existentes (`/api/*`, `/mcp/*`, `/docs*`, `/openapi.json`, frontend fallback).
**Dependencies:** Checkpoint 1
**Estimated scope:** XS (0-1 file)
**Acceptance Criteria:**
- Arquivos `.caddy` em `rules/` não aparecem em `git status`.
- O Caddyfile mantém 100% de compatibilidade e todas as rotas originais.
**Verification:**
- [ ] `touch substrate/deploy/vm/rules/test.caddy`
- [ ] `git status --porcelain substrate/deploy/vm/rules/` (retorna vazio)
- [ ] `rm substrate/deploy/vm/rules/test.caddy`

---

#### Task 5: Registrar no CHANGELOG e preparar branch upstream
**Description:** Registra a versão v0.8.1 no `CHANGELOG.md` do substrate detalhando a melhoria de deploy modular e instruções para o PR upstream.
**Dependencies:** `task-4`
**Estimated scope:** S (1 file)
**Acceptance Criteria:**
- `substrate/CHANGELOG.md` atualizado com a seção `[0.8.1]`.
**Verification:**
- [ ] `git diff substrate/CHANGELOG.md`
**Files:**
- `substrate/CHANGELOG.md`

---

### Checkpoint 2 (Final Verification)
- [ ] Subrepo `substrate/` 100% consistente e testado
- [ ] Pronto para comando `git subtree push` e PR no upstream `jmlapa/agentic-substrate`
