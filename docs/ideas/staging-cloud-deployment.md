# Idea: Staging Cloud Deployment via Single-VM Appliance

## Problem Statement
Como podemos empacotar e disponibilizar o Agentic Substrate para deploy público de staging em cloud própria (AWS EC2 ou GCP Compute Engine) com o menor custo e fricção operacional possíveis, garantindo estabilidade contra OOM, persistência íntegra do FalkorDB/Postgres e SSL automático sem problemas de CORS?

---

## Recommended Direction

Adotar a arquitetura **Turnkey Single-VM Appliance** utilizando **Docker Compose + Caddy 2**.

Essa abordagem replica com 100% de fidelidade a pilha que já roda em desenvolvimento, eliminando a complexidade de redes de microsserviços e garantindo persistência em disco SSD local com custo fixo e previsível (~US$ 25 a 35/mês).

### 1. Topologia da Infraestrutura

```text
                           Internet (Portas 80 / 443)
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    Caddy 2 (Reverse Proxy)    │
                       │  - Let's Encrypt TLS Automático│
                       │  - Terminação HTTPS Única     │
                       └───────────────┬───────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │ /                                   │ /api/*
                    ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐
        │  Frontend Console SPA │             │      API Gateway      │
        │   (React / Nginx:80)  │             │   (FastAPI / Uvicorn) │
        └───────────────────────┘             └───────────┬───────────┘
                                                          │
                    ┌─────────────────────────────────────┼─────────────────────────────────────┐
                    ▼                                     ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐             ┌───────────────────────┐
        │   PostgreSQL 16       │             │   Unified FalkorDB    │             │   Redis 7             │
        │   (+ pgvector)        │             │   (OpenCypher + HNSW) │             │   (Persistent Sagas)  │
        │   Volume: ./data/pg   │             │   Volume: ./data/fg   │             │   Volume: ./data/rd   │
        └───────────────────────┘             └───────────────────────┘             └───────────────────────┘
        ─────────────────────────────────────────────────────────────────────────────────────────────
                             VM Única (GCP e2-standard-2 / AWS t4g.medium - 8GB RAM, 50GB SSD)
```

### 2. Principais Vantagens para Validação de POC

1. **Persistência de Bloco Garantida:** Os dados de vetores e grafos no FalkorDB e os eventos no PostgreSQL residem em volumes locais montados no SSD da VM. Não há risco de perda de estado por reciclagem de containers efêmeros (problema clássico do Cloud Run).
2. **CORS Inexistente:** O Caddy atua como ponto único de entrada sob o mesmo domínio. Requisições do frontend para `/api` são roteadas internamente na rede Docker (`substrate_network`), dispensando regras complexas de pre-flight.
3. **Resiliência a Ingestões Pesadas (Anti-OOM):** A VM com 8GB de RAM oferece teto confortável para o processamento de PDFs pesados via MarkItDown, extração com PydanticAI v2 e indexação HNSW em memória no FalkorDB.
4. **Isolamento de Segurança:** Apenas as portas `80` e `443` ficam abertas no Firewall/Security Group da cloud. As portas de bancos (`5432`, `6379`, `6380`) e da API (`8000`) permanecem estritamente restritas à rede interna do Docker.

---

## Key Assumptions to Validate

- [ ] **Capacidade de Memória em Ingestão Simultânea:** Validar se a instância de 8GB de RAM suporta a ingestão concorrente de múltiplos documentos extensos (ex: 50+ páginas) sem atingir o limitador do OOM killer.
- [ ] **Desempenho de I/O no SSD da VM:** Garantir que a persistência contínua de AOF/RDB do FalkorDB e WAL do Postgres não atinjam gargalos de IOPS durante extrações intensivas de grafos.
- [ ] **Emissão de Certificado SSL pelo Caddy:** Validar que o Caddy emite e renova certificados Let's Encrypt automaticamente para o domínio ou IP público da VM sem necessidade de intervenção manual.
- [ ] **Idempotência do Script de Setup:** Garantir que o script de provisionamento (`setup-vm.sh`) possa ser executado em uma VM recém-criada (Ubuntu 22.04/24.04 LTS) e configure todo o ambiente em menos de 10 minutos.

---

## MVP Scope

### In-Scope (O que entra no MVP de Staging)
- **`deploy/staging/docker-compose.staging.yml`:** Definição otimizada dos containers com `restart: unless-stopped` e healthchecks estritos.
- **`deploy/staging/Caddyfile`:** Roteamento reverso de frontend e API com SSL automático e suporte a compressão.
- **`deploy/staging/.env.staging.example`:** Template de configuração com valores padrão seguros para staging.
- **`deploy/staging/setup-vm.sh`:** Script executável que instala Docker Engine, Docker Compose, clona/atualiza a aplicação, executa migrações do banco (`alembic upgrade head`) e inicia os serviços.
- **Documentação de Deploy no README:** Guia direto de "Como subir o ambiente de Staging em 3 passos" na GCP e na AWS.

### Not Doing (and Why)

- **GCP Cloud Run / AWS ECS Fargate com Bancos Gerenciados:** Descartado para a POC por exigir Cloud SQL, Memorystore e VPC Access (custo > US$ 180/mês) e por não haver serviço gerenciado nativo de FalkorDB na AWS/GCP, introduzindo risco alto de complexidade desnecessária.
- **Kubernetes / Helm Charts:** Desnecessário para validar o valor da POC. Adicionaria sobrecarga de gerenciamento de cluster (EKS/GKE) sem ganho imediato para um único ambiente de staging.
- **FalkorDB Cloud (SaaS Externo):** Descartado para manter toda a massa de dados do cliente isolada dentro da própria infraestrutura da VM na cloud, sem dependência de terceiros nem latência de rede externa.
- **Multi-region / Alta Disponibilidade (HA):** Fora de escopo para validação de POC. Foco estrito em estabilidade e simplicidade de 1 máquina.

---

## Open Questions

1. **Provedor Inicial de Cloud:** O primeiro teste prático de staging será realizado no **Google Cloud Platform (Compute Engine)** ou na **AWS (EC2)**?
2. **Resolução de Domínio:** Já existe um domínio ou subdomínio disponível para apontar o DNS para o IP da VM (ex: `staging.dominio.com`), ou utilizaremos um serviço dinâmico gratuito / IP público?
