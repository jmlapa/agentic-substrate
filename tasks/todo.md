# Tasks: Exclusão em Cascata de KBs, Documentos e Ontologias

- [x] Task 1: Domain Events e Aggregate Root
  - Acceptance: `DocumentDeletedEvent` e `KnowledgeBaseDeletedEvent` criados (single class per file); `KnowledgeBaseAggregate` suporta `remove_document(doc_id: UUID)`.
  - Verify: `uv run pytest tests/unit/test_knowledge_module.py`
  - Files: `src/modules/knowledge/domain/events/document_deleted_event.py`, `src/modules/knowledge/domain/events/knowledge_base_deleted_event.py`, `src/modules/knowledge/domain/aggregates/knowledge_base_aggregate.py`, `src/modules/knowledge/domain/events/__init__.py`

- [x] Task 2: Interfaces e Contratos de Portas
  - Acceptance: `IObjectStorage`, `IGraphStore`, `IKnowledgeBaseRepository`, `IOntologyRepository` atualizados com métodos de exclusão e checagem.
  - Verify: `uv run mypy src/modules/knowledge/domain/interfaces`
  - Files: `src/modules/knowledge/domain/interfaces/i_object_storage.py`, `src/modules/knowledge/domain/interfaces/i_graph_store.py`, `src/modules/knowledge/domain/interfaces/i_knowledge_base_repository.py`, `src/modules/knowledge/domain/interfaces/i_ontology_repository.py`

- [x] Task 3: Implementações nos Adaptadores de Infraestrutura
  - Acceptance: `LocalFileSystemStorageAdapter` remove arquivos/pastas; `FalkorDbGraphStoreAdapter` e `InMemoryGraphStore` removem subgrafo e grafo; `PostgresKnowledgeBaseRepository`, `PostgresOntologyRepository`, `InMemoryKnowledgeBaseRepository`, `InMemoryOntologyRepository` e `KnowledgeBaseProjector` realizam as exclusões.
  - Verify: `uv run pytest tests/unit/test_local_file_system_storage_adapter.py tests/unit/test_falkordb_graph_store_adapter.py tests/unit/test_postgres_repositories.py tests/unit/test_knowledge_base_projector.py`
  - Files: `src/modules/knowledge/infrastructure/adapters/local_file_system_storage_adapter.py`, `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`, `src/modules/knowledge/infrastructure/adapters/in_memory_graph_store.py`, `src/modules/knowledge/infrastructure/adapters/postgres_knowledge_base_repository.py`, `src/modules/knowledge/infrastructure/adapters/in_memory_knowledge_base_repository.py`, `src/modules/knowledge/infrastructure/adapters/postgres_ontology_repository.py`, `src/modules/knowledge/infrastructure/adapters/in_memory_ontology_repository.py`, `src/modules/knowledge/infrastructure/projections/knowledge_base_projector.py`

- [x] Task 4: Casos de Uso (Application Layer)
  - Acceptance: `DeleteKnowledgeBaseUseCase`, `DeleteDocumentUseCase` e `DeleteOntologyTemplateUseCase` implementados com Single Class per File e pattern `Result[T, E]`.
  - Verify: Novos testes unitários para cada use case em `tests/unit/`.
  - Files: `src/modules/knowledge/application/use_cases/delete_knowledge_base/*`, `src/modules/knowledge/application/use_cases/delete_document/*`, `src/modules/knowledge/application/use_cases/delete_ontology_template/*`, `src/modules/knowledge/application/use_cases/__init__.py`

- [x] Task 5: API Gateway Controllers e Injeção no Container
  - Acceptance: Endpoints `DELETE /api/v1/knowledge/bases/{kb_id}`, `DELETE /api/v1/knowledge/bases/{kb_id}/documents/{doc_id}`, `DELETE /api/v1/ontologies/{ontology_id}` registrados e validados no `AppContainer`.
  - Verify: `uv run pytest tests/integration/test_api_gateway.py`
  - Files: `src/api_gateway/controllers/knowledge_controller.py`, `src/api_gateway/controllers/ontology_controller.py`, `src/api_gateway/container.py`

- [x] Task 6: Frontend API Clients, Hooks e Páginas
  - Acceptance: Métodos em `knowledge-api.ts` e `ontologies-api.ts`, mutations nos hooks, modais de confirmação e botões de exclusão nas telas de listagem e detalhe.
  - Verify: `cd frontend && npm run build`
  - Files: `frontend/src/api/knowledge-api.ts`, `frontend/src/api/ontologies-api.ts`, `frontend/src/hooks/useKnowledgeBases.ts`, `frontend/src/hooks/useOntologies.ts`, `frontend/src/pages/knowledge-bases/KnowledgeBasesListPage.tsx`, `frontend/src/pages/knowledge-bases/KnowledgeBaseDetailPage.tsx`, `frontend/src/pages/ontologies/OntologiesListPage.tsx`, `frontend/src/pages/ontologies/OntologyDetailPage.tsx`

- [x] Task 7: Gates Finais de Qualidade e SDD
  - Acceptance: 100% testes passando, Mypy strict sem erros, Ruff sem erros, spec e changelog sincronizados.
  - Verify: `make pre-commit && cd frontend && npm run build`
  - Files: Todos os alterados.
