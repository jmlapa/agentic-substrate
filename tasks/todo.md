# Task List: CQRS Consolidated Read Model & Projections

## Phase 1: Database Migration & Schema Expansion

### Task 1: Alembic Migration `0006_expand_attached_documents_read_model.py`
- **Description:** Criar nova migration Alembic para adicionar colunas ricas de leitura na tabela relacional `attached_documents` (`enable_ocr`, `ocr_instructions`, `total_parents`, `total_children`, `indexed_nodes_count`, `indexed_edges_count`, `error_step`, `error_message`).
- **Acceptance criteria:**
  - [x] Migration Alembic gerada e encadeada após a `0005`.
  - [x] `upgrade()` adiciona todas as colunas com defaults apropriados.
  - [x] `downgrade()` reverte a remoção das colunas com segurança.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/test_migrations.py`
  - [x] Command: `alembic upgrade head`
- **Dependencies:** None
- **Files touched:**
  - `migrations/versions/0006_expand_attached_documents_read_model.py`
- **Estimated scope:** Small (1 file)

---

## Phase 2: Event-Driven Read Model Projector

### Task 2: Implementar `KnowledgeBaseProjector`
- **Description:** Criar `KnowledgeBaseProjector` em `src/modules/knowledge/infrastructure/projections/knowledge_base_projector.py` assinando os 8 eventos de domínio (`KnowledgeBaseCreatedEvent`, `DocumentAttachedEvent`, `DocumentStoredEvent`, `DocumentParsedToMarkdownEvent`, `DocumentChunkedEvent`, `GraphExtractedFromDocumentEvent`, `DocumentKnowledgeIndexedEvent`, `DocumentProcessingFailedEvent`) e sincronizando atomicamente as tabelas `knowledge_bases` e `attached_documents`.
- **Acceptance criteria:**
  - [x] Implementa Single Class per File.
  - [x] Trata cada evento com queries idempotentes (`ON CONFLICT DO UPDATE`).
  - [x] Operações 100% assíncronas com `asyncpg.Pool`.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/test_knowledge_base_projector.py`
- **Dependencies:** Task 1
- **Files touched:**
  - `src/modules/knowledge/infrastructure/projections/knowledge_base_projector.py`
  - `src/modules/knowledge/infrastructure/projections/__init__.py`
- **Estimated scope:** Medium (2 files)

---

### Task 3: Conectar o Projetor no Container de Injeção de Dependências
- **Description:** Registrar `KnowledgeBaseProjector` no `AppContainer` (`src/api_gateway/container.py`) e assinar os eventos no `EventBus` durante o bootstrap da aplicação.
- **Acceptance criteria:**
  - [x] Projetor instanciado no `AppContainer` quando o `EventBus` estiver configurado.
  - [x] Eventos disparados pelo `PostgresEventStore` fluem automaticamente para o projetor.
- **Verification:**
  - [x] Command: `uv run pytest tests/integration/test_container_configuration.py`
- **Dependencies:** Task 2
- **Files touched:**
  - `src/api_gateway/container.py`
- **Estimated scope:** Small (1 file)

---

## Checkpoint 1: Projeções Ativas e Sincronizadas
- [x] Testes de unidade do `KnowledgeBaseProjector` passando.
- [x] Migrations executadas e validadas no PostgreSQL.

---

## Phase 3: Repository & Read Model Queries

### Task 4: Atualizar `PostgresKnowledgeBaseRepository`
- **Description:** Atualizar `PostgresKnowledgeBaseRepository` para persistir `ontology_id` no `save`, e carregar o schema ontológico via `LEFT JOIN ontology_templates` e todas as métricas dos documentos no `get_by_id` e `list_all`.
- **Acceptance criteria:**
  - [x] `save()` persiste `ontology_id` na tabela `knowledge_bases`.
  - [x] `get_by_id()` executa `LEFT JOIN ontology_templates` e retorna o aggregate com `kb.ontology` preenchido.
  - [x] `get_by_id()` e `list_all()` retornam todos os campos enriquecidos de documentos (`total_parents`, `total_children`, etc.).
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/test_postgres_repositories.py`
- **Dependencies:** Task 3
- **Files touched:**
  - `src/modules/knowledge/infrastructure/adapters/postgres_knowledge_base_repository.py`
- **Estimated scope:** Small (1 file)

---

### Task 5: Streamline `KnowledgeController` para Consumo Direto do Repositório
- **Description:** Limpar `knowledge_controller.py` para consultar diretamente o repositório relacional consolidado `container.kb_repository.get_by_id` em $O(1)$, desacoplando leituras do `event_store`.
- **Acceptance criteria:**
  - [x] `GET /bases/{kb_id}` consulta `kb_repository.get_by_id` diretamente.
  - [x] `GET /bases` retorna a listagem completa com status consolidado.
- **Verification:**
  - [x] Command: `uv run pytest tests/integration/test_api_gateway.py`
- **Dependencies:** Task 4
- **Files touched:**
  - `src/api_gateway/controllers/knowledge_controller.py`
- **Estimated scope:** Small (1 file)

---

## Phase 4: Backfill & Sync Utility

### Task 6: Implementar Backfill / Replay de Projeções
- **Description:** Criar método `rebuild_projections()` ou utilitário no `KnowledgeBaseProjector` para repassar eventos passados do `EventStore` e garantir que qualquer base histórica seja consolidada nas tabelas relacionais.
- **Acceptance criteria:**
  - [x] Replay itera por todos os aggregates e atualiza o estado consolidado.
  - [x] Operação segura e idempotente.
- **Verification:**
  - [x] Command: `uv run pytest tests/unit/test_knowledge_base_projector.py`
- **Dependencies:** Task 5
- **Files touched:**
  - `src/modules/knowledge/infrastructure/projections/knowledge_base_projector.py`
  - `src/api_gateway/main.py`
- **Estimated scope:** Small (1 file)

---

## Phase 5: Especificações, ADR e Documentação

### Task 7: Criar `SPEC-consolidated-read-model-projections.md`, ADR 0006 e Atualizar `CAPABILITY-MAP.md`
- **Description:** Formalizar a arquitetura de Projeções CQRS no projeto, criando a spec do Marco 1.12, o ADR 0006 e atualizando o mapa de capacidades.
- **Acceptance criteria:**
  - [x] `SPEC-consolidated-read-model-projections.md` criado com objetivos, diagrama e contratos.
  - [x] `docs/decisions/0006-cqrs-read-model-projections.md` registrado.
  - [x] `CAPABILITY-MAP.md` atualizado com o Marco 1.12.
- **Verification:**
  - [x] Manual review dos documentos Markdown.
- **Dependencies:** Task 6
- **Files touched:**
  - `SPEC-consolidated-read-model-projections.md`
  - `docs/decisions/0006-cqrs-read-model-projections.md`
  - `CAPABILITY-MAP.md`
- **Estimated scope:** Medium (3 files)

---

## Checkpoint 2: Validação Completa e Gates de Qualidade
- [x] Executar suíte de testes unitários e de integração (`uv run pytest`).
- [x] Executar checagem de tipos estrita (`uv run mypy src tests`).
- [x] Executar formatador e linter (`uv run ruff check .` & `uv run ruff format --check .`).
- [x] Executar gate oficial `make pre-commit`.
- [x] Validar build do frontend (`cd frontend && npm run build`).


