.PHONY: help install lint format typecheck test test-cov check pre-commit clean dev run

help: ## Exibe os comandos disponíveis
	@echo "Agentic Substrate - Available Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependências do projeto com suporte a dev
	pip install -e ".[dev]"

lint: ## Executa o linter Ruff com auto-fix
	uv run ruff check --fix .

format: ## Formata o código usando Ruff
	uv run ruff format .

typecheck: ## Executa checagem estrita de tipos com Mypy
	uv run mypy src tests

test: ## Executa todos os testes com Pytest
	uv run pytest -v

test-cov: ## Executa testes gerando relatório de cobertura
	uv run pytest --cov=src --cov-report=term-missing -v

check: lint format typecheck test-cov ## Executa todos os linters, checagem de tipos e testes

pre-commit: check ## Gate de validação obrigatório antes de qualquer commit ou PR
	@echo "\033[32m✔ Todos os gates de qualidade passaram com sucesso. Pronto para commit!\033[0m"

dev: ## Sobe a infraestrutura local (Docker Compose)
	docker compose -f docker/docker-compose.yml up -d

dev-down: ## Para a infraestrutura local
	docker compose -f docker/docker-compose.yml down

run: ## Inicia a aplicação FastAPI localmente
	uvicorn src.api_gateway.main:app --reload --port 8000

clean: ## Limpa caches de Python, Pytest, Mypy e Ruff
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
