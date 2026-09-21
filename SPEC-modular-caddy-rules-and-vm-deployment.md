# Spec: Modular Caddy Environment Rules & Zero-Conflict VM Deployment

## 1. Objective

Desacoplar as regras de infraestrutura base do proxy reverso Caddy das particularidades locais de cada ambiente (como autenticação básica em staging, restrições de IP, cabeçalhos de segurança customizados ou certificados específicos). 

### O Problema
No modelo anterior, o arquivo `deploy/vm/Caddyfile` era monolítico e rastreado no Git. Qualquer operador ou desenvolvedor que precisasse proteger uma VM de homologação/staging com `basic_auth` ou ajustar para `:80` (IP público sem DNS/TLS) era forçado a editar o arquivo versionado diretamente no servidor. Isso gerava:
1. **Dirty working tree** na VM, bloqueando execuções de `git pull origin main`.
2. Uso forçado de `git stash` que, no subsequente `git stash pop`, causava conflitos silenciosos ou sobrescrevia rotas recém-adicionadas upstream (como ocorreu com o endpoint unificado `/mcp/*`).
3. Risco de vazamento acidental de credenciais e hashes bcrypt ao comitar arquivos modificados na máquina.

### A Solução
Adotar uma interface de extensão baseada em **inclusão declarativa por diretório de regras** (`rules/*.caddy`) montada no container Caddy com importação via wildcard. O Caddyfile rastreado permanece 100% estático e imutável no host, enquanto regras específicas de ambiente são injetadas como arquivos isolados e ignorados pelo Git.

---

## 2. Tech Stack & Dependencies

- **Edge Proxy**: `caddy:2.8-alpine` (suporte nativo a `import <glob>` idempotente).
- **Orquestrador de Containers**: Docker Engine 26+ com plugin Docker Compose v2.
- **Formato de Regras**: Caddyfile v2 (`basic_auth`, `header`, `remote_ip`, etc.).
- **Sistema Operacional Alvo**: Linux / Debian / Ubuntu LTS (x86_64 / arm64) e macOS / Linux local para desenvolvimento.

---

## 3. Commands

```bash
# 1. Validar sintaxe do Caddyfile base (sem regras customizadas)
docker run --rm -v $(pwd)/deploy/vm/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2.8-alpine caddy validate --config /etc/caddy/Caddyfile

# 2. Inicializar ou atualizar os serviços na VM (totalmente idempotente, sem stash)
cd deploy/vm
docker compose up -d --build

# 3. Recarregar configuração do Caddy em tempo de execução sem downtime
docker exec substrate_vm_caddy caddy reload --config /etc/caddy/Caddyfile

# 4. Ativar Basic Auth na VM (exemplo de uso zero-conflito)
cp deploy/vm/rules/auth.caddy.example deploy/vm/rules/auth.caddy
docker exec substrate_vm_caddy caddy reload --config /etc/caddy/Caddyfile

# 5. Atualizar o código do repositório na VM garantindo árvore sempre limpa
git pull origin main
# (Nunca mais falha com dirty tree)
```

---

## 4. Project Structure

```text
substrate/deploy/vm/
├── Caddyfile              → Configuração base imutável rastreada no Git (com wildcard import)
├── docker-compose.yml     → Orquestração All-in-One montando ./rules:/etc/caddy/rules:ro
├── .env.example           → Presets e documentação de DOMAIN_NAME=:80 para staging
├── setup.sh               → Script de inicialização idempotente (garante criação de rules/)
└── rules/                 → Ponto de extensão modular para o ambiente
    ├── .gitkeep           → Garante existência do diretório no clone limpo
    ├── README.md          → Documentação do contrato de extensões do Caddy
    ├── auth.caddy.example → Template documentado de Basic Auth com instruções de hash
    └── auth.caddy         → Arquivo local da VM (ignorado no .gitignore)
```

---

## 5. Interface Contract & Code Style

### 5.1 Contrato do `Caddyfile` Base
O bloco principal do site importa dinamicamente o glob `/etc/caddy/rules/*.caddy`. Se nenhum arquivo `.caddy` estiver presente, o Caddy ignora silenciosamente sem falhar:

```caddy
{
    # Global options
    email {$ACME_EMAIL:admin@example.com}
}

{$DOMAIN_NAME:localhost} {
    # Encode responses using modern compression algorithms
    encode zstd gzip

    # Environment-specific rules (e.g. basic_auth, ip filters, custom headers)
    # Dynamically imported if present in ./rules/ without modifying this file.
    import /etc/caddy/rules/*.caddy

    # API Gateway routes
    handle /api/* {
        reverse_proxy api:8000 {
            header_up X-Forwarded-Proto {scheme}
            header_up X-Forwarded-Host {host}
            header_up X-Real-IP {remote_host}
            flush_interval -1
        }
    }

    # Model Context Protocol (MCP) Streamable Server routes
    handle /mcp/* {
        reverse_proxy api:8000 {
            header_up X-Forwarded-Proto {scheme}
            header_up X-Forwarded-Host {host}
            header_up X-Real-IP {remote_host}
            flush_interval -1
        }
    }

    # OpenAPI / Swagger documentation
    handle /docs* {
        reverse_proxy api:8000
    }
    handle /openapi.json {
        reverse_proxy api:8000
    }

    # Frontend Console SPA routes
    handle {
        reverse_proxy frontend:80
    }
}
```

### 5.2 Contrato do `docker-compose.yml`
O serviço `caddy` monta o diretório `./rules` montado em `/etc/caddy/rules:ro`:

```yaml
  caddy:
    image: caddy:2.8-alpine
    container_name: substrate_vm_caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      - DOMAIN_NAME=${DOMAIN_NAME:-localhost}
      - ACME_EMAIL=${ACME_EMAIL:-admin@example.com}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./rules:/etc/caddy/rules:ro
      - ./data/caddy_data:/data
      - ./data/caddy_config:/config
    networks:
      - substrate_net
    depends_on:
      api:
        condition: service_healthy
      frontend:
        condition: service_healthy
```

### 5.3 Contrato de Exclusão no `.gitignore`
No `.gitignore` do projeto:

```gitignore
# Caddy local environment rules
deploy/vm/rules/*.caddy
substrate/deploy/vm/rules/*.caddy
!deploy/vm/rules/*.caddy.example
!substrate/deploy/vm/rules/*.caddy.example
```

---

## 6. Testing Strategy

1. **Teste de Sintaxe Limpa (Zero-Config / Dev):**
   - Garantir que o Caddy valida e inicia perfeitamente quando `rules/` contém apenas `.gitkeep` e `README.md`.
2. **Teste de Injeção de Regra Local (Staging Basic Auth):**
   - Criar `rules/auth.caddy` com diretiva `basic_auth`.
   - Disparar `caddy reload`.
   - Verificar que requisições sem credenciais recebem `401 Unauthorized`.
   - Verificar que requisições com credenciais corretas acessam tanto a API (`/api/*`), quanto o Frontend e o MCP (`/mcp/sse`).
3. **Teste de Imutabilidade do Git (Zero Dirty Tree):**
   - Executar `git status --porcelain` e validar que nenhuma alteração em `rules/*.caddy` suja a árvore.
   - Simular `git pull origin main` e certificar que a atualização ocorre sem atrito.

---

## 7. Boundaries

- **Always do:**
  - Usar sempre a sintaxe de wildcard `*.caddy` no `import` para garantir comportamento tolerante à ausência de regras.
  - Manter o volume montado como `:ro` (read-only) para o container Caddy.
  - Manter o fallback do frontend `handle { reverse_proxy frontend:80 }` sempre por último no `Caddyfile`.
  - Manter o suporte nativo a streaming SSE com `flush_interval -1` nas rotas `/mcp/*` e `/api/*`.
- **Ask first:**
  - Alterar portas públicas expostas pelo Caddy (80 e 443).
  - Alterar a ordem das diretivas de roteamento dentro do bloco principal.
- **Never do:**
  - Adicionar credenciais, senhas ou hashes de autenticação no arquivo `Caddyfile` rastreado.
  - Remover a exclusão do `.gitignore` para arquivos `.caddy`.
  - Forçar a existência obrigatória de arquivos em `rules/`.

---

## 8. Success Criteria

- [ ] O arquivo `deploy/vm/Caddyfile` contém `import /etc/caddy/rules/*.caddy` e valida sem erros com `caddy validate`.
- [ ] O `docker-compose.yml` mapeia `./rules:/etc/caddy/rules:ro`.
- [ ] O diretório `deploy/vm/rules/` contém `.gitkeep`, `README.md` e `auth.caddy.example`.
- [ ] Arquivos `.caddy` criados dentro de `rules/` não aparecem em `git status`.
- [ ] A documentação no `.env.example` orienta o uso de `DOMAIN_NAME=:80` para acesso direto por IP em staging sem TLS.
- [ ] Qualquer `git pull` futuro na VM funciona de forma 100% limpa e automatizada.
