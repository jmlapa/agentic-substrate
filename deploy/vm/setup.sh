#!/usr/bin/env bash
# ==============================================================================
# Agentic Substrate - Single-VM All-in-One Deployment Automation
# ==============================================================================
# Idempotent setup script for Debian/Ubuntu VMs (AWS EC2, GCP Compute Engine, etc.)
# Usage:
#   cd /path/to/agentic-substrate
#   bash deploy/vm/setup.sh
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> [1/6] Validando ambiente e pré-requisitos de sistema..."

# Função para invocar sudo apenas quando necessário
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    fi
fi

# Instalar Docker se não estiver instalado
if ! command -v docker >/dev/null 2>&1; then
    echo "Docker não encontrado. Instalando Docker Engine..."
    if command -v apt-get >/dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        $SUDO apt-get update -y
        $SUDO apt-get install -y curl ca-certificates gnupg
        curl -fsSL https://get.docker.com | $SUDO sh
    else
        echo "AVISO: Gerenciador de pacotes apt-get não encontrado. Por favor, instale o Docker manualmente." >&2
        exit 1
    fi
fi

# Garantir que o plugin Docker Compose v2 está presente
if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose v2 não encontrado. Instalando plugin compose..."
    if command -v apt-get >/dev/null 2>&1; then
        $SUDO apt-get update -y
        $SUDO apt-get install -y docker-compose-plugin
    else
        echo "ERRO: docker compose v2 não encontrado." >&2
        exit 1
    fi
fi

echo "✔ Docker e Docker Compose v2 estão disponíveis."

echo "==> [2/6] Verificando configuração de variáveis de ambiente (.env)..."
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"

if [ ! -f "${ENV_FILE}" ]; then
    echo "Arquivo .env não encontrado em ${SCRIPT_DIR}. Gerando a partir de .env.example..."
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    
    # Gerar uma senha segura para o PostgreSQL
    NEW_PG_PASS="$(openssl rand -hex 16 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(16))' 2>/dev/null || echo "pg_$(date +%s)_substrate")"
    
    # Substituir POSTGRES_PASSWORD no .env gerado
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/POSTGRES_PASSWORD=postgres/POSTGRES_PASSWORD=${NEW_PG_PASS}/" "${ENV_FILE}"
    else
        sed -i "s/POSTGRES_PASSWORD=postgres/POSTGRES_PASSWORD=${NEW_PG_PASS}/" "${ENV_FILE}"
    fi
    echo "✔ .env gerado com sucesso com credenciais seguras para o PostgreSQL."
else
    echo "✔ Arquivo .env existente detectado (mantendo configurações e segredos)."
fi

# Verificar aviso sobre chaves de LLM
if ! grep -q -E "^(OPENROUTER_API_KEY|GEMINI_API_KEY)=..*" "${ENV_FILE}"; then
    echo "⚠️  ATENÇÃO: Nenhuma chave de API detectada (OPENROUTER_API_KEY ou GEMINI_API_KEY) no .env."
    echo "    Edite ${ENV_FILE} para adicionar suas chaves antes de realizar ingestões ou síntese GraphRAG."
fi

# Orientação sobre Google Drive Service Account
if grep -q -E "^GOOGLE_APPLICATION_CREDENTIALS=..*" "${ENV_FILE}"; then
    echo "ℹ️  Google Drive Service Account configurada em GOOGLE_APPLICATION_CREDENTIALS."
fi

echo "==> [3/6] Preparando diretórios locais de persistência de dados..."
mkdir -p "${SCRIPT_DIR}/data/postgres"
mkdir -p "${SCRIPT_DIR}/data/falkordb"
mkdir -p "${SCRIPT_DIR}/data/redis"
mkdir -p "${SCRIPT_DIR}/data/storage"
mkdir -p "${SCRIPT_DIR}/data/caddy_data"
mkdir -p "${SCRIPT_DIR}/data/caddy_config"
mkdir -p "${SCRIPT_DIR}/rules"
mkdir -p "${SCRIPT_DIR}/credentials"

# Configurar permissões nos diretórios de banco e credenciais sensíveis
chmod 700 "${SCRIPT_DIR}/data/postgres" || true
chmod 700 "${SCRIPT_DIR}/data/falkordb" || true
chmod 700 "${SCRIPT_DIR}/data/redis" || true
chmod 700 "${SCRIPT_DIR}/credentials" || true
echo "✔ Diretórios locais de dados persistentes e credenciais prontos."

echo "==> [4/6] Inicializando containers no modo All-in-One..."
docker compose --project-directory "${SCRIPT_DIR}" -f "${SCRIPT_DIR}/docker-compose.yml" up -d --build

echo "==> [5/6] Aguardando inicialização saudável do PostgreSQL e da API..."
MAX_RETRIES=30
RETRY_COUNT=0
HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    API_STATUS="$(docker inspect --format='{{.State.Health.Status}}' substrate_vm_api 2>/dev/null || echo "starting")"
    if [ "${API_STATUS}" = "healthy" ]; then
        HEALTHY=true
        break
    fi
    echo "Aguardando containers ficarem saudáveis... (${RETRY_COUNT}/${MAX_RETRIES}) - Status API: ${API_STATUS}"
    sleep 3
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ "$HEALTHY" = false ]; then
    echo "AVISO: A API demorou mais que o esperado para responder como healthy."
    echo "Verifique os logs com: docker compose --project-directory ${SCRIPT_DIR} -f ${SCRIPT_DIR}/docker-compose.yml logs"
fi

echo "==> [6/6] Executando migrações do banco de dados (Alembic)..."
docker compose --project-directory "${SCRIPT_DIR}" -f "${SCRIPT_DIR}/docker-compose.yml" exec -T api alembic upgrade head || echo "AVISO: Falha ao rodar migrações automaticamente. Execute manualmente quando a API estiver pronta."

echo ""
echo "=============================================================================="
echo "✔ Agentic Substrate - Deploy All-in-One Concluído com Sucesso!"
echo "=============================================================================="
DOMAIN_VALUE="$(grep -E '^DOMAIN_NAME=' "${ENV_FILE}" | cut -d '=' -f2- || echo "localhost")"
echo "Acesso Web (Frontend): http://${DOMAIN_VALUE} ou https://${DOMAIN_VALUE}"
echo "Documentação da API:  http://${DOMAIN_VALUE}/docs"
echo ""
echo "Comandos úteis para gerenciar a VM:"
echo "  Ver status:   docker compose -f ${SCRIPT_DIR}/docker-compose.yml ps"
echo "  Ver logs:     docker compose -f ${SCRIPT_DIR}/docker-compose.yml logs -f api"
echo "  Parar:        docker compose -f ${SCRIPT_DIR}/docker-compose.yml down"
echo "=============================================================================="
