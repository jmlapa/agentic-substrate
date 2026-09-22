# Task List: Saga Concurrency Resilience (Marco 1.26)

- [x] Task 1: Adicionar Mutex por KB e Helper de Mutação Atômica com Retry no Saga Coordinator
  - Acceptance: `DocumentIngestionSagaCoordinator` possui `_execute_atomic_aggregate_mutation` com retry exponencial jittered para `DomainError("Concurrency conflict")`.
  - Verify: Mypy strict e ruff sem erros.
  - Files: `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`

- [x] Task 2: Refatorar Handlers da Saga para Usar Deferred Atomic Commit
  - Acceptance: Todos os 4 handlers (`handle_document_stored`, `handle_document_parsed`, `handle_document_chunked`, `handle_graph_extracted`) executam o trabalho assíncrono em paralelo e salvam estados (sucesso e erro) via `_execute_atomic_aggregate_mutation`.
  - Verify: Testes existentes de saga passando com `poetry run pytest tests/modules/knowledge/application/sagas/`.
  - Files: `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`

- [x] Task 3: Atualizar ReprocessDocumentUseCase para Suportar Documentos Presos em CHUNKED
  - Acceptance: O caso de uso aceita documentos com status `CHUNKED` e emite o evento para retomar a ingestão a partir dos chunks persistidos.
  - Verify: Teste unitário de `ReprocessDocumentUseCase`.
  - Files: `src/modules/knowledge/application/use_cases/reprocess_document/reprocess_document_use_case.py`

- [x] Task 4: Criar Suíte de Testes Automatizados de Concorrência e Resiliência
  - Acceptance: Testes cobrindo ingestão paralela de 5 documentos para o mesmo aggregate e recuperação automática sob simulação de `Concurrency conflict`.
  - Verify: `poetry run pytest tests/modules/knowledge/application/test_document_ingestion_saga_concurrency.py -v`.
  - Files: `tests/modules/knowledge/application/test_document_ingestion_saga_concurrency.py`

- [x] Task 5: Validar Gates de Qualidade com make pre-commit
  - Acceptance: 100% dos testes passando (314+), Mypy strict sem erros, Ruff check e format 100% limpos.
  - Verify: `make pre-commit` retorna código 0.
  - Files: Nenhum (validação global).

- [x] Task 6: Reiniciar Contêiner e Recuperar Documentos Travados em Produção
  - Acceptance: Disparar reprocessamento para os 3 documentos pendentes (`4483722f...`, `5506c4df...`, `b93ce975...`) e confirmar que todos alcançam `INDEXED` com nós/arestas no FalkorDB.
  - Verify: Consulta na API `GET /api/v1/knowledge/bases/18d634c4-6c5b-4273-b0b3-cc00433b8be4` retorna `status: "INDEXED"` para todos.
  - Files: Nenhum (operação em runtime).
