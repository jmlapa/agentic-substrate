# Implementation Plan: Exclusão em Cascata de KBs, Documentos e Ontologias

## Overview
Implementação do fluxo de exclusão de ponta a ponta (Frontend SPA + API Gateway + Application UseCases + Domain Events + Storage Cleanups + FalkorDB Subgraph/Graph Deletion + PostgreSQL Read Models & Repositories) para Knowledge Bases, Documentos e Templates de Ontologia.

---

## Architecture & Design Decisions

1. **Domain Events & Aggregate Cleanup:**
   - Adicionar `DocumentDeletedEvent` e `KnowledgeBaseDeletedEvent` em `src/modules/knowledge/domain/events/`.
   - Adicionar métodos `remove_document(doc_id: UUID)` no aggregate `KnowledgeBaseAggregate`.
2. **Ports / Interfaces:**
   - `IObjectStorage`: Adicionar `delete_object(path: str) -> None` e `delete_prefix(prefix: str) -> None`.
   - `IGraphStore`: Adicionar `delete_document_subgraph(kb_id: UUID, doc_id: UUID) -> None` e `delete_graph(kb_id: UUID) -> None`.
   - `IKnowledgeBaseRepository`: Adicionar `delete_by_id(kb_id: UUID) -> None` e `delete_document(kb_id: UUID, doc_id: UUID) -> None`.
   - `IOntologyRepository`: Adicionar `delete_by_id(id: UUID) -> None` e `count_usages(ontology_id: UUID) -> int`.
3. **Application Layer (Single Class per File):**
   - Use Case `DeleteKnowledgeBaseUseCase` (`delete_knowledge_base_request.py`, `delete_knowledge_base_response.py`, `delete_knowledge_base_use_case.py`).
   - Use Case `DeleteDocumentUseCase` (`delete_document_request.py`, `delete_document_response.py`, `delete_document_use_case.py`).
   - Use Case `DeleteOntologyTemplateUseCase` (`delete_ontology_template_request.py`, `delete_ontology_template_response.py`, `delete_ontology_template_use_case.py`).
4. **Infrastructure Layer Adapters & Projections:**
   - `LocalFileSystemStorageAdapter`: Implementar remoção de arquivo e remoção recursiva de pasta de partição.
   - `FalkorDbGraphStoreAdapter` e `InMemoryGraphStore`: Implementar remoção de nós do documento e exclusão de grafo da KB.
   - `PostgresKnowledgeBaseRepository` e `InMemoryKnowledgeBaseRepository`: Implementar deletes atômicos no Postgres e in-memory.
   - `PostgresOntologyRepository` e `InMemoryOntologyRepository`: Implementar remoção e checagem de uso em `knowledge_bases`.
   - `KnowledgeBaseProjector`: Atualizar handlers para remover rows em `attached_documents` e `knowledge_bases`.
5. **API Gateway Layer:**
   - `DELETE /api/v1/knowledge/bases/{kb_id}`
   - `DELETE /api/v1/knowledge/bases/{kb_id}/documents/{document_id}`
   - `DELETE /api/v1/ontologies/{ontology_id}`
6. **Frontend Layer (SPA Console):**
   - Atualizar `api/knowledge-api.ts` e `api/ontologies-api.ts` com métodos `deleteBase`, `deleteDocument` e `deleteOntology`.
   - Atualizar `hooks/useKnowledgeBases.ts` e `hooks/useOntologies.ts` com mutations de exclusão.
   - Adicionar botões de exclusão e modal de confirmação em `KnowledgeBasesListPage`, `KnowledgeBaseDetailPage`, `OntologiesListPage` e `OntologyDetailPage`.

---

## Verification Checkpoints
- `make pre-commit` ou `uv run pytest`, `uv run ruff check .`, `uv run mypy src tests`.
- `cd frontend && npm run build`.
