# Implementation Plan: PostgreSQL Persistence & Dead Code Cleanup

## Overview
Substituir todas as implementações em memória de ontologias e bases de conhecimento (`InMemoryOntologyRepository`, `InMemoryKnowledgeBaseRepository`) por adaptadores relacionais persistentes no PostgreSQL (`PostgresOntologyRepository`, `PostgresKnowledgeBaseRepository`). Além disso, inicializar o pool de conexões assíncronas `asyncpg` no ciclo de vida (lifespan) da aplicação FastAPI, executar migrações Alembic automaticamente e remover códigos mortos/shims obsoletos, garantindo que ontologias, KBs e documentos persistam permanentemente mesmo após reinicializações e rebuilds de containers Docker.

---

## Architecture Decisions
1. **Modelagem Relacional no PostgreSQL (Alembic Migration 0005):**
   - Tabela `ontology_templates`: `id` (UUID PK), `name` (VARCHAR), `description` (TEXT), `version` (INT), `node_types` (JSONB), `relationship_types` (JSONB), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ).
   - Tabela `knowledge_bases`: `id` (UUID PK), `name` (VARCHAR), `description` (TEXT), `ontology_id` (UUID FK nullable), `status` (VARCHAR), `storage_partition` (VARCHAR), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ).
   - Tabela `attached_documents`: `id` (UUID PK), `kb_id` (UUID FK cascade), `file_name` (VARCHAR), `status` (VARCHAR), `storage_path` (VARCHAR), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ).
2. **Single Class per File & Hexagonal Repositories:**
   - `PostgresOntologyRepository` em `src/modules/knowledge/infrastructure/adapters/postgres_ontology_repository.py`.
   - `PostgresKnowledgeBaseRepository` em `src/modules/knowledge/infrastructure/adapters/postgres_knowledge_base_repository.py`.
   - Tipagem estrita com Mypy (`asyncpg.Pool` / `asyncpg.Connection`) e Result pattern nos casos de uso.
3. **Lifespan Assíncrono com Auto-Migração e Conexão Robusta:**
   - `src/api_gateway/main.py` gerencia o ciclo de vida via `@asynccontextmanager` do FastAPI: inicializa o pool `asyncpg`, executa `alembic upgrade head` programaticamente se configurado, e injeta o container configurado com os adaptadores do PostgreSQL.
   - Fallback para `InMemory*` apenas durante testes unitários onde não houver pool configurado.
4. **Remoção de Código Morto:**
   - Auditar e remover arquivos não utilizados, unificar referências de chunker para `StructureTolerantMarkdownChunker` e limpar imports/shims redundantes.

---

## Task List

### Phase 1: Database Schema & Migrations
- [ ] **Task 1: Migration Alembic 0005 para Ontologias e Knowledge Bases**
  - Criar migração `migrations/versions/0005_create_knowledge_bases_and_ontologies_tables.py` com tabelas `ontology_templates`, `knowledge_bases` e `attached_documents`.
- [ ] **Task 2: Modelos / Mapeamentos DDL e Índices de Performance**
  - Adicionar índices em `knowledge_bases.name`, `attached_documents.kb_id` e chaves estrangeiras.

### Checkpoint: Migrations Verified
- [ ] `uv run alembic upgrade head` executa sem erros criando as 3 tabelas no Postgres local.

---

### Phase 2: PostgreSQL Repository Adapters
- [ ] **Task 3: Implementar `PostgresOntologyRepository`**
  - Implementar métodos `save`, `get_by_id`, `get_by_name`, `list_all` em `src/modules/knowledge/infrastructure/adapters/postgres_ontology_repository.py`.
- [ ] **Task 4: Implementar `PostgresKnowledgeBaseRepository`**
  - Implementar métodos `save`, `get_by_id`, `list_all`, `add_document`, `update_document_status` em `src/modules/knowledge/infrastructure/adapters/postgres_knowledge_base_repository.py`.
- [ ] **Task 5: Testes Unitários e de Integração dos Repositórios Postgres**
  - Criar suite de testes em `tests/unit/test_postgres_repositories.py` e `tests/integration/test_postgres_repositories.py`.

### Checkpoint: Repositories Verified
- [ ] Testes de repositórios passando com 100% de sucesso.

---

### Phase 3: Lifespan, IoC Container & Startup Automation
- [ ] **Task 6: Configurar Lifespan do FastAPI e Factory Dinâmica no `AppContainer`**
  - Atualizar `src/api_gateway/main.py` com lifespan assíncrono para gerenciar pool `asyncpg` e registrar o container em `app.state`.
  - Atualizar `src/api_gateway/container.py` para instanciar `PostgresOntologyRepository` e `PostgresKnowledgeBaseRepository` quando o pool do Postgres estiver ativo.
- [ ] **Task 7: Execução Automática de Migrações no Startup do Container**
  - Adicionar comando de inicialização ou script no container `api` para rodar migrações antes de iniciar o Uvicorn (`alembic upgrade head && uvicorn ...`).

### Checkpoint: Container Persistence Working
- [ ] Reiniciar containers e validar que ontologias e KBs continuam salvas no PostgreSQL.

---

### Phase 4: Dead Code Cleanup & Quality Gates
- [ ] **Task 8: Limpeza de Código Morto e Refatorações de Chunker/Extractor**
  - Limpar imports obsoletos, avaliar dependência de `MarkdownParentChildChunker` e garantir que o projeto use exclusivamente os padrões canônicos.
- [ ] **Task 9: Execução dos Gates Oficiais (`make pre-commit`, `npm run build`, `make dev`)**
  - Executar suíte completa de lint, mypy strict, testes com cobertura >= 90% e teste ponta a ponta no Frontend.

### Checkpoint: Complete
- [ ] Todos os gates aprovados e persistência validada no navegador.

---

## Risks and Mitigations
| Risco | Impacto | Mitigação |
|---|---|---|
| Diferença de schema JSON entre Pydantic e colunas `JSONB` | Médio | Usar `.model_dump(mode='json')` e `TypeAdapter` para serialização/deserialização determinística dos nós e relações. |
| Conexão do Postgres não pronta no startup do container | Médio | O `docker-compose.yml` já usa `depends_on: postgres: condition: service_healthy`. Adicionar retentativa no lifespan. |
| Quebra de retrocompatibilidade em testes unitários existentes | Baixo | Manter os adaptadores `InMemory*` disponíveis para testes rápidos de unidade sem dependência de Postgres. |

---

## Open Questions
- Nenhuma no momento. O escopo e os contratos estão alinhados com a arquitetura hexagonal existente.
