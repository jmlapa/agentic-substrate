# Spec: Single-VM All-in-One Deployment Module

## 1. Objective
Disponibilizar um modo de deploy **All-in-One em VM Única** (`deploy/vm/`) que permita a qualquer desenvolvedor, startup ou equipe de engenharia publicar o **Agentic Substrate** em uma máquina virtual própria (AWS EC2, GCP Compute Engine, Hetzner ou DigitalOcean) com um único comando, garantindo:
- Custo fixo e previsível (~US$ 25 a 35/mês).
- Persistência íntegra em SSD de bloco para PostgreSQL 16 (+ pgvector), FalkorDB e Redis.
- Proxy reverso Caddy 2 com terminação TLS/HTTPS automática (Let's Encrypt) e eliminação total de problemas de CORS entre Frontend SPA e API Gateway.
- Isolamento estrito de portas (apenas 80 e 443 públicas; portas de banco e backend restritas à rede interna do Docker).
- Script de setup automatizado e idempotente para sistemas baseados em Debian/Ubuntu.

---

## 2. Tech Stack & Dependencies
- **Orquestrador de Containers**: Docker Engine 26+ com Docker Compose v2 plugin.
- **Edge Proxy & SSL**: `caddy:2.8-alpine` (emissão automática de certificados Let's Encrypt, compressão gzip/zstd, buffer para SSE).
- **Backend API**: Python 3.12/3.13, FastAPI, Uvicorn, MarkItDown, PydanticAI v2 (`Dockerfile`).
- **Frontend Console**: Nginx 1.27-alpine servindo o build estático do React 18 / Vite SPA (`frontend/Dockerfile`).
- **Banco Relacional & Event Store**: `pgvector/pgvector:0.8.6-pg16`.
- **Banco de Grafos & HNSW Vector**: `falkordb/falkordb:v4.20.3-alpine`.
- **Fila de Tarefas & Sagas**: `redis:7.4.10-alpine`.
- **Sistema Operacional Alvo da VM**: Ubuntu 22.04 LTS ou Ubuntu 24.04 LTS (x86_64 / arm64).

---

## 3. Commands

```bash
# 1. Provisionar a VM com Docker, Compose e dependências de sistema
bash deploy/vm/setup.sh

# 2. Iniciar todos os serviços em background no modo All-in-One
docker compose -f deploy/vm/docker-compose.yml up -d

# 3. Verificar o status e healthcheck de todos os containers
docker compose -f deploy/vm/docker-compose.yml ps

# 4. Acompanhar logs em tempo real
docker compose -f deploy/vm/docker-compose.yml logs -f [api|frontend|caddy|falkordb|postgres|redis]

# 5. Executar migrações do banco de dados na VM
docker compose -f deploy/vm/docker-compose.yml exec api alembic upgrade head

# 6. Parar os serviços
docker compose -f deploy/vm/docker-compose.yml down

# 7. Parar e reiniciar após atualização de código/imagem
docker compose -f deploy/vm/docker-compose.yml pull && docker compose -f deploy/vm/docker-compose.yml up -d --build
```

---

## 4. Project Structure

```text
deploy/
└── vm/
    ├── docker-compose.yml     → Orquestração All-in-One (caddy, api, frontend, postgres, falkordb, redis)
    ├── Caddyfile              → Configuração de proxy reverso, HTTPS automático e rotas (/ e /api/*)
    ├── .env.example           → Template de variáveis com presets seguros para deploy em VM
    └── setup.sh               → Script de 1 comando (instalação do Docker, configuração e inicialização)
docs/
└── ideas/
    └── staging-cloud-deployment.md → Artefato conceitual de refinamento da arquitetura
```

---

## 5. Gestão de Configuração e Variáveis de Ambiente (.env)

O modo All-in-One separa estritamente **variáveis de topologia interna** (que já vêm pré-configuradas) de **segredos do usuário**:

### 1. Separação de Responsabilidades no `.env.example`
- **Presets Internos da VM (Zero-Config para o usuário):**
  - `POSTGRES_HOST=postgres`, `POSTGRES_PORT=5432`, `POSTGRES_DB=agentic_substrate`
  - `FALKORDB_HOST=falkordb`, `FALKORDB_PORT=6379`
  - `REDIS_HOST=redis`, `REDIS_PORT=6379`
  - `STORAGE_TYPE=local`, `STORAGE_LOCAL_BASE_DIR=/app/data/storage`
- **Variáveis que o Deployer (Usuário ou Terraform) precisa fornecer:**
  - `DOMAIN_NAME`: Domínio público apontado para o IP da VM (ou `localhost`/IP para teste local)
  - `ACME_EMAIL`: E-mail para emissão automática do certificado TLS Let's Encrypt no Caddy
  - `OPENROUTER_API_KEY` e/ou `GEMINI_API_KEY`: Credenciais para extração e síntese
  - `POSTGRES_PASSWORD`: Senha do PostgreSQL (gerada automaticamente se omitida)

### 2. Padrões de Injeção de Variáveis pelo Usuário

#### Padrão A: Provisionamento Automatizado via Terraform / Cloud-Init (Recomendado para Usuários)
Quem provisionar a VM via Terraform (ou Ansible/Pulumi) pode injetar o `.env` no `user_data` / `cloud-init` antes de disparar o setup:
```hcl
# Exemplo conceitual no Terraform do usuário (fora do repo):
resource "aws_instance" "appliance" {
  user_data = <<-EOF
    #!/bin/bash
    git clone https://github.com/usuario/agentic-substrate.git /opt/agentic-substrate
    cat <<'ENV' > /opt/agentic-substrate/deploy/vm/.env
    DOMAIN_NAME="staging.meudominio.com"
    ACME_EMAIL="devops@meudominio.com"
    OPENROUTER_API_KEY="${var.openrouter_api_key}"
    GEMINI_API_KEY="${var.gemini_api_key}"
    POSTGRES_PASSWORD="${random_password.db.result}"
    ENV
    cd /opt/agentic-substrate && bash deploy/vm/setup.sh
  EOF
}
```

#### Padrão B: Provisionamento Manual via SSH
O desenvolvedor acessa a VM recém-criada via SSH:
```bash
git clone https://github.com/usuario/agentic-substrate.git
cd agentic-substrate/deploy/vm
cp .env.example .env
nano .env  # Preenche DOMAIN_NAME, ACME_EMAIL e API Keys
bash setup.sh
```

### 3. Comportamento Idempotente do `setup.sh`
- Se `deploy/vm/.env` **já existir** (injetado via Terraform, Secrets Manager ou manualmente), o `setup.sh` o preserva e apenas valida se as chaves mínimas estão presentes.
- Se **não existir**, o `setup.sh` cria a partir de `.env.example`, gera um `POSTGRES_PASSWORD` seguro via `openssl rand -hex 16` e orienta o usuário sobre o preenchimento das API keys.

---

## 6. Architectural Topology & Code Style

### Topologia de Rede e Portas
```text
                           Internet (Portas 80 / 443)
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    Caddy 2 (Edge / Reverse)   │
                       │  - Portas: 80:80, 443:443     │
                       │  - Let's Encrypt TLS          │
                       └───────────────┬───────────────┘
                                       │ (Rede interna Docker: substrate_net)
                    ┌──────────────────┴──────────────────┐
                    │ /                                   │ /api/*
                    ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐
        │  Frontend Console SPA │             │      API Gateway      │
        │  (container: frontend)│             │    (container: api)   │
        │  Porta interna: 80    │             │   Porta interna: 8000 │
        └───────────────────────┘             └───────────┬───────────┘
                                                          │
                    ┌─────────────────────────────────────┼─────────────────────────────────────┐
                    ▼                                     ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐             ┌───────────────────────┐
        │   PostgreSQL 16       │             │   Unified FalkorDB    │             │   Redis 7             │
        │   (+ pgvector)        │             │   (OpenCypher + HNSW) │             │   (Persistent Sagas)  │
        │   Porta interna: 5432 │             │   Porta interna: 6379 │             │   Porta interna: 6379 │
        │   Volume: ./data/pg   │             │   Volume: ./data/fg   │             │   Volume: ./data/rd   │
        └───────────────────────┘             └───────────────────────┘             └───────────────────────┘
```

### Regras de Configuração do Caddyfile
```caddy
{
    email {$ACME_EMAIL}
}

{$DOMAIN_NAME:localhost} {
    # Compressão zstd e gzip
    encode zstd gzip

    # Roteamento da API Gateway
    handle /api/* {
        reverse_proxy api:8000 {
            header_up X-Forwarded-Proto {scheme}
            header_up X-Real-IP {remote_host}
        }
    }

    # Documentação Swagger / OpenAPI
    handle /docs* {
        reverse_proxy api:8000
    }
    handle /openapi.json {
        reverse_proxy api:8000
    }

    # Roteamento do Frontend SPA
    handle {
        reverse_proxy frontend:80
    }
}
```

---

## 7. Testing Strategy

1. **Validação Sintática e Linter do Compose**:
   `docker compose -f deploy/vm/docker-compose.yml config` deve validar sem erros de parsing ou variáveis não declaradas.
2. **Verificação de Healthcheck de Inicialização**:
   - `postgres`: `pg_isready -U postgres -d agentic_substrate`
   - `falkordb`: `redis-cli ping`
   - `redis`: `redis-cli ping`
   - `api`: `curl -f http://localhost:8000/health`
   - `frontend`: `curl -f http://localhost:80/`
   - `caddy`: resposta 200/301 nas portas 80/443.
3. **Persistência de Estado após Reinício**:
   Criar uma Knowledge Base de teste, reiniciar os containers com `docker compose down && docker compose up -d` e verificar se os dados do Postgres e do FalkorDB continuam íntegros sem perda de nós.
4. **Isolamento de Portas**:
   Garantir que a partir da internet externa (host), portas `5432`, `6379` e `8000` **NÃO** respondam, confirmando que não há binding `0.0.0.0:5432` no host.

---

## 8. Boundaries

- **Always**:
  - Expor publicamente no host apenas as portas `80` e `443` (através do Caddy).
  - Usar volumes nomeados ou diretórios mapeados no host com permissões corretas para retenção de dados.
  - Exigir arquivo `.env` para credenciais sensíveis (OpenRouter, Gemini, Postgres Password).
  - Manter dependência estrita com healthchecks (`depends_on: condition: service_healthy`).
- **Ask first**:
  - Adicionar novos containers ou serviços auxiliares (ex: Prometheus, Grafana).
  - Alterar versões padrão dos bancos de dados.
- **Never**:
  - Hardcodar API keys ou senhas no `docker-compose.yml` ou no `Caddyfile`.
  - Expor o FalkorDB ou PostgreSQL diretamente para a internet pública sem autenticação e VPN.
  - Apagar pastas de volume no script de `setup.sh`.

---

## 9. Success Criteria

- [ ] Arquivo `deploy/vm/docker-compose.yml` funcional com os 6 serviços coordenados (`caddy`, `api`, `frontend`, `postgres`, `falkordb`, `redis`).
- [ ] Arquivo `deploy/vm/Caddyfile` configurado para roteamento unificado de `/api` e `/` com SSL automático.
- [ ] Arquivo `deploy/vm/.env.example` atualizado e documentado com instruções diretas para preenchimento.
- [ ] Script `deploy/vm/setup.sh` criado com suporte a instalação limpa no Ubuntu (instalação do Docker Engine e Compose v2, validação de pré-requisitos, inicialização dos serviços).
- [ ] Seção no `README.md` documentando o procedimento de deploy em VM única com 1 comando.
- [ ] `CAPABILITY-MAP.md` atualizado com o módulo de deploy e seus status.
- [ ] Todos os gates de qualidade do projeto (`make pre-commit`) continuam passando com 100% de sucesso.
