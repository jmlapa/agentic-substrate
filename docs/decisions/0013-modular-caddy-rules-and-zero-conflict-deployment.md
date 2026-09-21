# ADR-0013: Regras Modulares no Caddy e Deploy Zero-Conflito em VM

## Status
Accepted

## Data
2026-09-21

## Contexto
O modo de deploy em VM única do Agentic Substrate (`deploy/vm/`) utiliza o Caddy 2 como proxy reverso de borda. No entanto, ambientes reais de homologação/staging e produção possuem requisitos específicos que não devem ser versionados no repositório público, tais como:
1. **Proteção de Acesso:** Necessidade de autenticação básica (`basic_auth`) ou whitelisting de IPs para bloquear tráfego público antes do lançamento oficial.
2. **Topologia de Acesso:** Em ambientes de staging sem domínio ou DNS registrado, o acesso ocorre via IP público direto na porta 80 (`:80`), dispensando a negociação TLS/ACME do Let's Encrypt.

### Causa Raiz do Problema Operacional
Anteriormente, o `Caddyfile` era monolítico. Os operadores na VM eram forçados a editar o arquivo rastreado diretamente no servidor. Isso gerava uma **árvore de trabalho suja** (`dirty git tree`). Ao rodar `git pull`, o Git recusava a atualização; ao recorrer a `git stash` e `git stash pop`, ocorriam sobrescritas de alterações upstream (apagando, por exemplo, rotas novas como `/mcp/*`).

## Decisão

1. **Ponto de Extensão Declarativo no Caddy:**
   - Adicionada a diretiva `import /etc/caddy/rules/*.caddy` no bloco do site no `Caddyfile`.
   - O uso de wildcard (`*.caddy`) é idempotente e tolerante: caso nenhum arquivo exista no diretório, o Caddy ignora a diretiva sem erros, garantindo compatibilidade local instantânea.

2. **Montagem de Volume no Docker Compose:**
   - Adicionado o volume `./rules:/etc/caddy/rules:ro` no serviço `caddy` em `docker-compose.yml`.

3. **Isolamento no Git (`.gitignore`):**
   - Configurada a exclusão `deploy/vm/rules/*.caddy`, exceto arquivos `.example`.
   - Regras locais na VM (como `auth.caddy`) nunca constam no `git status`.

4. **Templates e Documentação:**
   - Criado `deploy/vm/rules/auth.caddy.example` com instruções de geração de hash bcrypt.
   - Atualizado `.env.example` documentando o uso de `DOMAIN_NAME=:80` para acesso direto via IP.

## Consequências

### Positivas
- **Deploy Zero-Conflito:** O comando `git pull origin main` na VM nunca mais é bloqueado por alterações no Caddyfile.
- **Segurança de Credenciais:** Hashes e senhas ficam isolados em arquivos não versionados no servidor.
- **Zero Downtime Reload:** Alterações de regras locais podem ser aplicadas instantaneamente com `caddy reload` sem reiniciar containers.
- **Transparência Total:** A rota `/mcp/*` e futuras rotas upstream permanecem preservadas em qualquer atualização.
