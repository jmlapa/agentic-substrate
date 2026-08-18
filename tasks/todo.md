# Task List: PostgreSQL Persistence & Dead Code Cleanup

## Phase 1: Database Schema & Migrations

### Task 1: Migration Alembic 0005 para Ontologias e Knowledge Bases
- **Description:** Criar a migração `migrations/versions/0005_create_knowledge_bases_and_ontologies_tables.py` contendo as tabelas `ontology_templates`, `knowledge_bases` e `attached_documents` com tipos UUID, JSONB e TIMESTAMPTZ.
- **Acceptance criteria:**
  - [ ] Tabela `ontology_templates` criada com colunas `id`, `name` (unique), `description`, `version`, `node_types`, `relationship_types`, `created_at`, `updated_at`.
  - [ ] Tabela `knowledge_bases` criada com colunas `id`, `name`, `description`, `ontology_id` (FK para `ontology_templates.id` ON DELETE SET NULL), `status`, `storage_partition`, `created_at`, `updated_at`.
  - [ ] Tabela `attached_documents` criada com colunas `id`, `kb_id` (FK para `knowledge_bases.id` ON DELETE CASCADE), `file_name`, `status`, `storage_path`, `created_at`, `updated_at`.
  - [ ] Funções `upgrade()` e `downgrade()` completas e idempotentes.
- **Verification:**
  - [ ] Command: `uv run alembic upgrade head`
- **Dependencies:** None
- **Files likely touched:**
  - `migrations/versions/0005_create_knowledge_bases_and_ontologies_tables.py`
- **Estimated scope:** Small (1 file)

---

### Task 2: Índices e Validação de DDL
- **Description:** Adicionar índices nas tabelas relacionais (`idx_knowledge_bases_name`, `idx_attached_docs_kb_id`) para garantir buscas rápidas por nome e por partição de KB.
- **Acceptance criteria:**
  - [ ] Índices criados e validados no script de migração.
- **Verification:**
  - [ ] Command: `uv run alembic upgrade head`
- **Dependencies:** Task 1
- **Files likely touched:**
  - `migrations/versions/0005_create_knowledge_bases_and_ontologies_tables.py`
- **Estimated scope:** Small (1 file)

---

## Checkpoint: Migrations Verified
- [ ] Migração 0005 aplicada com sucesso e tabelas criadas no banco.

---

## Phase 2: PostgreSQL Repository Adapters

### Task 3: Implementar `PostgresOntologyRepository`
- **Description:** Implementar `PostgresOntologyRepository(IOntologyRepository)` usando `asyncpg.Pool` para salvar, buscar por id, buscar por nome e listar templates de ontologias.
- **Acceptance criteria:**
  - [ ] Implementa todos os métodos de `IOntologyRepository` (`save`, `get_by_id`, `get_by_name`, `list_all`).
  - [ ] Serialização e desserialização de `NodeTypeDefinition` e `RelationshipTypeDefinition` via Pydantic TypeAdapter / JSONB.
  - [ ] Regra Single Class per File respeitada.
- **Verification:**
  - [ ] Tests pass: `uv run pytest tests/unit/test_postgres_ontology_repository.py`
  - [ ] Mypy: `uv run mypy src/modules/knowledge/infrastructure/adapters/postgres_ontology_repository.py --strict`
- **Dependencies:** Task 1
- **Files likely touched:**
  - `src/modules/knowledge/infrastructure/adapters/postgres_ontology_repository.py`
  - `src/modules/knowledge/infrastructure/adapters/__init__.py`
- **Estimated scope:** Medium (2-3 files)

---

### Task 4: Implementar `PostgresKnowledgeBaseRepository`
- **Description:** Implementar `PostgresKnowledgeBaseRepository(IKnowledgeBaseRepository)` usando `asyncpg.Pool` para gerenciar agregados de Knowledge Base e seus documentos vinculados de forma relacional.
- **Acceptance criteria:**
  - [ ] Implementa `save`, `get_by_id`, `list_all`, `add_document`, `update_document_status`.
  - [ ] Mapeia para o aggregate root `KnowledgeBaseAggregate` e entidades `AttachedDocument`.
  - [ ] Regra Single Class per File respeitada.
- **Verification:**
  - [ ] Tests pass: `uv run pytest tests/unit/test_postgres_knowledge_base_repository.py`
  - [ ] Mypy: `uv run mypy src/modules/knowledge/infrastructure/adapters/postgres_knowledge_base_repository.py --strict`
- **Dependencies:** Task 1
- **Files likely touched:**
  - `src/modules/knowledge/infrastructure/adapters/postgres_knowledge_base_repository.py`
  - `src/modules/knowledge/infrastructure/adapters/__init__.py`
- **Estimated scope:** Medium (2-3 files)

---

### Task 5: Testes Unitários e de Integração dos Repositórios Postgres
- **Description:** Criar testes automatizados para validar todas as operações CRUD e transacionais dos repositórios PostgreSQL.
- **Acceptance criteria:**
  - [ ] Testes unitários com mocks de conexão e testes de integração com banco real passando.
- **Verification:**
  - [ ] Command: `uv run pytest tests/unit/test_postgres_*.py`
- **Dependencies:** Task 3, Task 4
- **Files likely touched:**
  - `tests/unit/test_postgres_ontology_repository.py`
  - `tests/unit/test_postgres_knowledge_base_repository.py`
- **Estimated scope:** Medium (2 files)

---

## Checkpoint: Repositories Verified
- [ ] Repositórios Postgres testados e aprovados com 100% de cobertura.

---

## Phase 3: Lifespan, IoC Container & Startup Automation

### Task 6: Configurar Lifespan do FastAPI e Factory Dinâmica no `AppContainer`
- **Description:** Adicionar gerenciamento assíncrono de ciclo de vida (lifespan) no `src/api_gateway/main.py`, criando o pool `asyncpg` no startup e fechando no shutdown. Atualizar `create_app_container` para instanciar repositórios Postgres quando `postgres_pool` for fornecido.
- **Acceptance criteria:**
  - [ ] FastAPI inicializa pool `asyncpg` na inicialização e o injeta no `AppContainer`.
  - [ ] `create_app_container` instancia `PostgresOntologyRepository`, `PostgresKnowledgeBaseRepository` e `PostgresEventStore` automaticamente.
  - [ ] Se o banco estiver indisponível em ambiente de teste, fallback gracioso para `InMemory*`.
- **Verification:**
  - [ ] Tests pass: `uv run pytest tests/integration/test_api_gateway.py`
- **Dependencies:** Task 5
- **Files likely touched:**
  - `src/api_gateway/main.py`
  - `src/api_gateway/container.py`
- **Estimated scope:** Medium (2-3 files)

---

### Task 7: Execução Automática de Migrações no Startup do Container
- **Description:** Configurar a inicialização do container backend no `docker-compose.yml` ou script de entrypoint para rodar `alembic upgrade head` antes de iniciar o Uvicorn, garantindo que o schema esteja sempre atualizado.
- **Acceptance criteria:**
  - [ ] Container `api` executa migrações no startup sem falhas.
  - [ ] Containers sobem com dados persistentes que sobrevivem a `docker compose restart`.
- **Verification:**
  - [ ] Command: `docker compose -f docker/docker-compose.yml up -d --build`
- **Dependencies:** Task 6
- **Files likely touched:**
  - `Dockerfile`
  - `docker/docker-compose.yml`
- **Estimated scope:** Small (2 files)

---

## Checkpoint: Container Persistence Working
- [ ] Dados criados na API ou Frontend continuam disponíveis após reiniciar os containers.

---

## Phase 4: Dead Code Cleanup & Quality Gates

### Task 8: Limpeza de Código Morto e Refatorações
- **Description:** Auditar a base de código para remover imports não utilizados, código morto ou comentários obsoletos.
- **Acceptance criteria:**
  - [ ] Zero código morto ou variáveis não utilizadas.
  - [ ] Ruff check limpo sem warnings.
- **Verification:**
  - [ ] Command: `uv run ruff check .`
- **Dependencies:** Task 7
- **Files likely touched:**
  - Diversos arquivos em `src/` e `tests/`
- **Estimated scope:** Medium (3-5 files)

---

### Task 9: Execução dos Gates Oficiais (`make pre-commit`, `npm run build`, `make dev`)
- **Description:** Executar a suíte completa de qualidade para fechar a entrega.
- **Acceptance criteria:**
  - [ ] `make pre-commit` 100% aprovado.
  - [ ] `npm run build` no frontend 100% aprovado.
  - [ ] Validação visual no Frontend com Ontologia e KB persistidas.
- **Verification:**
  - [ ] Command: `make pre-commit`
- **Dependencies:** Task 8
- **Files likely touched:**
  - `CHANGELOG.md`
- **Estimated scope:** Small (1 file)

---

## Checkpoint: Complete
- [ ] Todo o sistema operando com persistência total em PostgreSQL e FalkorDB.
