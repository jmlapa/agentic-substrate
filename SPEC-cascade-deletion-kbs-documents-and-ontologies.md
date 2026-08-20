# Spec: Exclusão em Cascata de Knowledge Bases, Documentos e Templates de Ontologia

## Objective
Implementar a funcionalidade completa de exclusão de **Knowledge Bases (KBs)**, **Documentos Individuais** e **Templates de Ontologia** no ecossistema Agentic Substrate. A exclusão deve ser consistente e atômica nos múltiplos subsistemas de persistência:
1. **PostgreSQL (Event Store & Read Model CQRS)**: Limpeza das tabelas relacionais (`knowledge_bases`, `attached_documents`, `ontology_templates`) e propagação via eventos de domínio.
2. **Object Storage (Local FileSystem)**: Limpeza dos artefatos binários brutos, markdowns convertidos, páginas renderizadas e checkpoints de ToC/Saga.
3. **FalkorDB (Graph Store)**: Exclusão completa do grafo da KB ou remoção direcionada de nós de Documentos, ParentChunks, ChildChunks e conexões estruturais/semânticas.
4. **API Gateway (FastAPI)**: Endpoints REST `DELETE` com validações de integridade referencial.
5. **Frontend Console (React SPA)**: Ações visuais com Modais de Confirmação destrutiva e feedback de erro/sucesso.

---

## Tech Stack & Abstrações Envolvidas

- **Backend:** Python 3.12+, FastAPI, asyncpg, FalkorDB client, aiofiles.
- **Padrões de Arquitetura:** Hexagonal / Clean Architecture, DDD, CQRS, Event Sourcing, Result[T, E], Single Class per File.
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS, TanStack React Query, Lucide Icons.

---

## Regras de Negócio e Comportamento por Entidade

### 1. Exclusão de Template de Ontologia (`DELETE /api/v1/ontologies/{ontology_id}`)
- **Verificação de Dependência:** Uma ontologia **não** pode ser excluída se estiver vinculada a uma ou mais Knowledge Bases ativas.
  - Query de checagem: `SELECT COUNT(*) FROM knowledge_bases WHERE ontology_id = $1`.
  - Se `COUNT > 0`, retornar `Err(code="CONFLICT", message="Não é possível excluir uma ontologia vinculada a bases de conhecimento existentes.")` gerando HTTP 409 Conflict.
- **Efeito da Exclusão:** Remove o registro de `ontology_templates` no Postgres (e repositório in-memory nos testes).

### 2. Exclusão de Documento (`DELETE /api/v1/knowledge/bases/{kb_id}/documents/{document_id}`)
- **Verificação:** A KB e o documento devem existir.
- **Event Sourcing & Aggregate:** O aggregate `KnowledgeBaseAggregate` emite o evento `DocumentDeletedEvent(aggregate_id=kb_id, document_id=doc_id)`. O aggregate remove o documento de seu dicionário interno `self.documents`.
- **Projeção Read Model:** `KnowledgeBaseProjector` assina `DocumentDeletedEvent` e executa:
  `DELETE FROM attached_documents WHERE id = $1 AND kb_id = $2;`
- **Limpeza no Object Storage:** O storage remove os arquivos do documento:
  - Arquivo original: `kb-{kb_id}/raw/{doc_id}-*`
  - Arquivo markdown: `kb-{kb_id}/processed/{doc_id}-*`
  - Checkpoints: `kb-{kb_id}/checkpoints/{doc_id}-*`
- **Limpeza no FalkorDB:** O adaptador do grafo executa Cypher direcionado:
  ```cypher
  MATCH (d:Document {id: $doc_id})
  OPTIONAL MATCH (d)-[:HAS_PARENT]->(p:ParentChunk)
  OPTIONAL MATCH (p)-[:CONTAINS_CHILD]->(c:ChildChunk)
  DETACH DELETE d, p, c
  ```

### 3. Exclusão de Knowledge Base (`DELETE /api/v1/knowledge/bases/{kb_id}`)
- **Verificação:** A KB deve existir.
- **Event Sourcing & Aggregate:** O aggregate emite `KnowledgeBaseDeletedEvent(aggregate_id=kb_id)`.
- **Projeção Read Model:** O projector remove os registros em `attached_documents` e `knowledge_bases` associados ao `kb_id`.
- **Limpeza no Object Storage:** Remove recursivamente todo o diretório da partição: `data/storage/kb-{kb_id}/`.
- **Limpeza no FalkorDB:** Executa a exclusão de todo o grafo nomeado `kb_{kb_id}`:
  `client.select_graph(graph_name).delete()`

---

## Commands

```bash
# Backend Tests & Verification
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests

# Frontend Build & Typecheck
cd frontend && npm run build
```

---

## Project Structure & Novos Arquivos (Single Class per File)

```
src/
  modules/
    knowledge/
      domain/
        events/
          document_deleted_event.py
          knowledge_base_deleted_event.py
        interfaces/
          i_object_storage.py (Adição de delete_object, delete_prefix)
          i_graph_store.py (Adição de delete_document_subgraph, delete_knowledge_base_graph)
          i_knowledge_base_repository.py (Adição de delete_by_id, delete_document_by_id)
          i_ontology_repository.py (Adição de delete_by_id, count_knowledge_bases_using_ontology)
      application/
        use_cases/
          delete_knowledge_base/
            __init__.py
            delete_knowledge_base_request.py
            delete_knowledge_base_response.py
            delete_knowledge_base_use_case.py
          delete_document/
            __init__.py
            delete_document_request.py
            delete_document_response.py
            delete_document_use_case.py
          delete_ontology_template/
            __init__.py
            delete_ontology_template_request.py
            delete_ontology_template_response.py
            delete_ontology_template_use_case.py
      infrastructure/
        adapters/
          local_file_system_storage_adapter.py (Implementação de delete_object, delete_prefix)
          falkordb_graph_store_adapter.py (Implementação de delete_document_subgraph, delete_graph)
          postgres_knowledge_base_repository.py (Implementação de delete_by_id, delete_document_by_id)
          postgres_ontology_repository.py (Implementação de delete_by_id, count_knowledge_bases_using_ontology)
        projections/
          knowledge_base_projector.py (Handlers para DocumentDeletedEvent e KnowledgeBaseDeletedEvent)
  api_gateway/
    controllers/
      knowledge_controller.py (Endpoints DELETE /bases/{id} e DELETE /bases/{id}/documents/{doc_id})
      ontology_controller.py (Endpoint DELETE /ontologies/{id})
frontend/
  src/
    api/
      knowledge-api.ts (Métodos deleteBase, deleteDocument)
      ontologies-api.ts (Método deleteOntology)
    pages/
      knowledge-bases/
        KnowledgeBasesListPage.tsx (Botão e modal de exclusão de KB)
        KnowledgeBaseDetailPage.tsx (Botão de exclusão da KB e botão de exclusão de documento)
      ontologies/
        OntologiesListPage.tsx (Botão e modal de exclusão de Ontologia)
        OntologyDetailPage.tsx (Botão de exclusão da Ontologia)
```

---

## Testing Strategy

1. **Testes Unitários:**
   - Exclusão de KB com mock de storage, graph store e repository.
   - Exclusão de documento com limpeza de nós no graph store e remoção de arquivo no storage.
   - Exclusão de ontologia livre (sucesso) e ontologia vinculada a KB (retorna erro de conflito).
2. **Testes de Integração:**
   - Teste dos endpoints `DELETE /api/v1/knowledge/bases/{kb_id}` e `DELETE /api/v1/knowledge/bases/{kb_id}/documents/{doc_id}` via `TestClient`.
   - Teste do endpoint `DELETE /api/v1/ontologies/{ontology_id}` verificando status 200 e 409 quando há conflito.
3. **Frontend Verification:**
   - `npm run build` garantindo zero erros de tipagem TypeScript.

---

## Boundaries

- **Always:**
  - Manter a regra estrita de *Single Class per File*.
  - Garantir tipagem estrita com Mypy e formatação com Ruff.
  - Confirmar exclusões com modal destrutivo no frontend antes de disparar as requisições.
- **Ask first:**
  - Se for necessário alterar o esquema de tabelas relacionais do banco via Alembic.
- **Never:**
  - Deletar dados no Postgres sem limpar os arquivos correspondentes no ObjectStorage e grafos no FalkorDB.
  - Permitir exclusão silenciosa de ontologias em uso sem aviso de conflito.

---

## Success Criteria

1. Todas as 3 entidades (Knowledge Base, Documento, Template de Ontologia) podem ser excluídas com sucesso pelo backend e frontend.
2. Ao excluir uma Knowledge Base, seu storage em disco (`data/storage/kb-*`) e seu grafo no FalkorDB são completamente removidos.
3. Ao excluir um Documento, seus chunks e nós no FalkorDB, seus arquivos em disco e seus dados na tabela `attached_documents` são removidos.
4. Ao tentar excluir uma Ontologia em uso por uma KB, a API retorna erro amigável 409 e o frontend exibe o motivo ao usuário.
5. 100% dos testes unitários e de integração passam e o build do frontend compila perfeitamente.
