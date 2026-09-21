# Implementation Plan: Modular Caddy Environment Rules & Zero-Conflict VM Deployment (Marco 1.23)

## 1. Overview

Implementar o desacoplamento de regras de ambiente no Caddy 2 para o modo de deploy em VM única (`deploy/vm/`), permitindo que configurações específicas (como Basic Auth em staging, whitelists de IP e cabeçalhos customizados) sejam injetadas como arquivos isolados na pasta `rules/` sem modificar o `Caddyfile` versionado pelo Git. Isso elimina árvores de trabalho sujas (`dirty working tree`) na VM e garante que operações de atualização (`git pull origin main`) sejam 100% limpas e idempotentes, prevenindo sobrescritas acidentais de rotas (como ocorrido com `/mcp/*`).

---

## 2. Architecture Decisions

- **Wildcard Import Idempotente:** O `Caddyfile` base utiliza `import /etc/caddy/rules/*.caddy`. Por usar wildcard, o Caddy ignora silenciosamente se o diretório estiver vazio, preservando backward compatibility total.
- **Read-Only Container Mount:** O diretório `./rules` é montado como `:ro` no container Caddy, garantindo imutabilidade em runtime a partir do container.
- **Git Tracking Isolation:** Arquivos `.caddy` em `rules/` são ignorados no `.gitignore`, garantindo que regras locais nunca constem no `git status` da VM.
- **Template Declarativo Documentado:** Um arquivo `auth.caddy.example` fornece aos operadores um modelo pronto para cópia rápida com documentação do utilitário `caddy hash-password`.
- **Parametrização via `.env`:** O `DOMAIN_NAME` suporta `:80` nativamente para VMs sem apontamento DNS/TLS.

---

## 3. Dependency Graph

```
[Task 1] Atualizar Caddyfile e docker-compose.yml no deploy/vm
    │
    └── [Task 2] Criar estrutura de rules/ (.gitkeep, README.md, auth.caddy.example)
            │
            └── [Task 3] Atualizar .gitignore, setup.sh e .env.example
                    │
                    └── [Task 4] Validação de sintaxe Caddyfile e testes de isolamento
                            │
                            └── [Task 5] Atualizar CHANGELOG.md e preparar branch upstream
```

---

## 4. Phase Breakdown

### Phase 1: Core Configuration (Tasks 1 e 2)
- Adicionar `import /etc/caddy/rules/*.caddy` no `deploy/vm/Caddyfile`.
- Montar `./rules:/etc/caddy/rules:ro` no `deploy/vm/docker-compose.yml`.
- Criar a pasta `deploy/vm/rules/` com `.gitkeep`, `README.md` e `auth.caddy.example`.

### Phase 2: Environment & Git Isolation (Task 3)
- Adicionar exclusões de `rules/*.caddy` no `.gitignore` (do substrate e da raiz).
- Atualizar `deploy/vm/setup.sh` para garantir `mkdir -p ${SCRIPT_DIR}/rules`.
- Atualizar `deploy/vm/.env.example` documentando `DOMAIN_NAME=:80` para staging.

### Phase 3: Validação e Documentação (Tasks 4 e 5)
- Testar e validar a sintaxe do Caddyfile.
- Validar `git status` com arquivos `.caddy` simulados.
- Atualizar `CHANGELOG.md` e registrar o commit para subtree push upstream.

---

## 5. Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Caddy falhar ao inicializar sem arquivos em `rules/` | Alto | Uso estrito de wildcard (`*.caddy`), que o Caddy v2 trata como glob opcional sem disparar erro. |
| Operador comitar arquivo de senha na VM | Alto | Adição explícita no `.gitignore` e verificação nos gates locais. |
| Conflitos em futuros merges do subtree | Médio | Commits estritamente focados na pasta `deploy/vm/` e documentação aderente ao ADR-009. |
