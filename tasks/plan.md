# Implementation Plan: CQRS Consolidated Read Model & Projections

## Overview
Implementar a separação estrita de **Comando (Write Model)** e **Consulta (Read Model)** através de **Projeções de Eventos (Event-Driven Projector)** no PostgreSQL.
Isso garante que:
1. **O Write Model (Agregado & Sagas):** Continua sendo hidratado via **Event Sourcing** a partir do histórico de eventos (`domain_events`), assegurando invariantes de domínio e controle de versão otimista (`expected_version`).
2. **O Read Model (Consultas HTTP & Frontend):** É mantido sincronizado em tabelas relacionais consolidadas (`knowledge_bases` e `attached_documents`), respondendo a queries `GET /bases` e `GET /bases/{id}` em $O(1)$ tempo constante com `JOIN` nas ontologias, métricas completas de chunks e nós, sem necessidade de replay de eventos em tempo de leitura.

---

## Architecture Decisions
1. **CQRS & Projector Pattern (Single Class per File):**
   - Criar `KnowledgeBaseProjector` em `src/modules/knowledge/infrastructure/projections/knowledge_base_projector.py`.
   - O projetor escuta os 8 eventos de domínio do ciclo de vida da KB e atualiza de forma atômica e idempotente as tabelas relacionais `knowledge_bases` e `attached_documents`.
2. **Evolução do Schema Relacional (Alembic Migration):**
   - Migration `0006_expand_attached_documents_read_model.py` adicionando colunas ricas em `attached_documents`:
     `enable_ocr`, `ocr_instructions`, `total_parents`, `total_children`, `indexed_nodes_count`, `indexed_edges_count`, `error_step`, `error_message`.
3. **Repositório Relacional Completo (`PostgresKnowledgeBaseRepository`):**
   - `save`: Grava todas as colunas (incluindo `ontology_id`).
   - `get_by_id`: Executa `LEFT JOIN ontology_templates` e agrega documentos com métricas completas, sem depender de replay do EventStore em leituras.
   - `list_all`: Retorna listagem com contagens reais e schemas consolidados.
4. **Backfill & Replay Utility:**
   - Utilitário para reprocessar eventos legados do `domain_events` e popular/reparar projeções relacionais sob demanda.

---

## Task List

### Phase 1: Database Migration & Schema Expansion
- [ ] **Task 1: Alembic Migration `0006_expand_attached_documents_read_model.py`**
  - Adicionar colunas de OCR, métricas de chunks, contadores de nós/arestas e detalhes de erro na tabela `attached_documents`.

### Phase 2: Event-Driven Read Model Projector
- [ ] **Task 2: Implementar `KnowledgeBaseProjector`**
  - Criar `KnowledgeBaseProjector` em `src/modules/knowledge/infrastructure/projections/knowledge_base_projector.py` assinando os eventos de domínio via `EventBus`.
- [ ] **Task 3: Conectar o Projetor no Container de Injeção de Dependências**
  - Registrar o projetor no `AppContainer` (`src/api_gateway/container.py`) para subscrição automática no ciclo de vida da aplicação.

### Checkpoint 1: Projeções Ativas
- [ ] Testes de unidade do `KnowledgeBaseProjector` passando.
- [ ] Migrations executadas e validadas no PostgreSQL.

### Phase 3: Repository & Read Model Queries
- [ ] **Task 4: Atualizar `PostgresKnowledgeBaseRepository`**
  - Ajustar queries SQL com `LEFT JOIN ontology_templates` e hidratação completa dos campos de documentos.
- [ ] **Task 5: Ajustar `KnowledgeController` para Consumo Direto do Repositório**
  - Manter o controller focado no Read Model do repositório, delegando a responsabilidade de projeção exclusivamente ao projetor.

### Phase 4: Backfill & Sync Utility
- [ ] **Task 6: Implementar Backfill / Replay de Projeções**
  - Criar rotina para reconstruir o estado das tabelas relacionais a partir do `EventStore` para bases existentes.

### Phase 5: Especificações, ADR e Documentação
- [ ] **Task 7: Criar `SPEC-consolidated-read-model-projections.md` e ADR 0006**
  - Documentar a arquitetura CQRS/Projector e atualizar `CAPABILITY-MAP.md` e `SPEC-migrations.md`.

### Checkpoint 2: Validação Completa
- [ ] Executar suíte de testes unitários e de integração (`uv run pytest`).
- [ ] Executar o gate oficial `make pre-commit`.

---

## Risks and Mitigations
| Risco | Impacto | Mitigação |
|---|---|---|
| Dessincronização entre EventStore e Read Model em falha transitória | Médio | Transações assíncronas no Postgres e rotina de replay/backfill idempotente. |
| Bases de conhecimento criadas antes da migration | Baixo | Replay de inicialização sincroniza automaticamente eventos pré-existentes. |
| Overhead de escrita no EventBus | Baixo | Queries no Projector utilizam índices em chaves primárias e estrangeiras indexadas ($O(1)$). |
