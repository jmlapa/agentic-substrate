# Implementation Plan: Single-VM All-in-One Deployment (Marco 1.21)

## 1. Overview

Disponibilizar o módulo `deploy/vm/` que permite subir o **Agentic Substrate** completo (FastAPI, React Console SPA, PostgreSQL com pgvector, FalkorDB, Redis e Caddy 2 com SSL automático) em uma única máquina virtual (AWS EC2, GCP Compute Engine, etc.) com um único comando. O plano é dividido em 5 tarefas incrementais e verificáveis.

---

## 2. Architecture Decisions

- **Modo All-in-One Estrito:** Todos os componentes rodam na mesma VM compartilhando uma rede interna Docker bridge isolada (`substrate_net`).
- **Segurança por Padrão (Zero DB Port Exposure):** Nenhuma porta de banco de dados (`5432`, `6379`, `6380`) ou backend (`8000`) é exposta ao host (`0.0.0.0`). Apenas `80` e `443` do Caddy são públicas.
- **Persistência de Bloco no Host:** Volumes mapeados no SSD da máquina (`./data/...`) garantem que o FalkorDB (grafo + vetores HNSW), PostgreSQL (event store + tabelas) e Redis (sagas) nunca percam dados em reinícios de containers.
- **Caddy como Reverse Proxy & Ingress Único:** Serve o frontend SPA em `/`, roteia `/api/*` e `/docs` para a API Gateway e gera certificados Let's Encrypt automaticamente.
- **Automação Idempotente (`setup.sh`):** Suporta execução automatizada via Terraform/cloud-init (se o `.env` já estiver presente) ou manual via SSH.

---

## 3. Dependency Graph

```
[Task 1] Templates de Configuração & Proxy (deploy/vm/.env.example, deploy/vm/Caddyfile)
    │
    └── [Task 2] Orquestração Docker Compose All-in-One (deploy/vm/docker-compose.yml)
            │
            └── [Task 3] Script de Automação e Provisionamento (deploy/vm/setup.sh)
                    │
                    └── [Task 4] Suíte de Testes Automatizados de Configuração (tests/unit/test_deploy_vm_configuration.py)
                            │
                            └── [Task 5] Documentação no README.md e Gate Final (make pre-commit)
```

---

## 4. Phase Breakdown

### Phase 1: Configuração e Proxy Core (Task 1)
Criação do template `.env.example` com presets de infraestrutura interna e do `Caddyfile` com regras de roteamento reverso, compressão e suporte a SSE.

### Phase 2: Orquestração All-in-One (Task 2)
Criação do `deploy/vm/docker-compose.yml` coordenando os 6 containers com healthchecks, ordem estrita de inicialização e persistência local.

### Phase 3: Script de Setup Idempotente (Task 3)
Criação do `deploy/vm/setup.sh` com instalação automática do Docker/Compose, geração de senha segura de banco, verificação de `.env` e subida com migração.

### Phase 4: Validação Automatizada (Task 4)
Implementação de testes unitários que validam sintaxe do YAML, isolamento de portas, consistência de variáveis com `AppSettings` e validade do script bash.

### Phase 5: Documentação e Gate de Qualidade (Task 5)
Atualização do `README.md` com instruções de deploy em VM e execução do gate completo `make pre-commit`.

---

## 5. Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Variáveis desincronizadas entre `.env.example` e `AppSettings` | Médio | Teste automatizado validando que toda variável essencial exigida pelo backend está no template. |
| Portas de banco expostas acidentalmente para a internet pública | Alto | Teste unitário inspecionando o Compose para garantir que apenas Caddy tem bindings de portas no host. |
| Ingestão massiva causando OOM na VM | Alto | Documentação formal exigindo VM com mínimo de 8GB de RAM (GCP `e2-standard-2` ou AWS `t4g.medium`). |
| Script `setup.sh` quebrando em ambientes sem `sudo` interativo | Médio | Detecção de privilégios de root / uso não interativo de apt (`DEBIAN_FRONTEND=noninteractive`). |
