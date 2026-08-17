# Lista de Tarefas: Markdown Parent-Child Chunking & Gemini Embedding 2 (Marco 1.6)

## Fase 1: Primitivas de Domínio, Value Objects, Protocolos e Eventos

### Tarefa 1: Implementar Value Objects de Chunking (`ParentChunk`, `ChildChunk`, `DocumentChunkCollection`)
**Descrição:** Criar os Value Objects imutáveis responsáveis por modelar o particionamento hierárquico de documentos Markdown no domínio do módulo `knowledge`, respeitando a regra de Single Class per File.
**Critérios de Aceite:**
- [ ] Arquivo `src/modules/knowledge/domain/value_objects/child_chunk.py` criado contendo `ChildChunk` com `id`, `parent_chunk_id`, `chunk_index`, `header_path`, `content`, `embedding` e `metadata`.
- [ ] Arquivo `src/modules/knowledge/domain/value_objects/parent_chunk.py` criado contendo `ParentChunk` com `id`, `header_path`, `content`, `token_count` e `metadata`.
- [ ] Arquivo `src/modules/knowledge/domain/value_objects/document_chunk_collection.py` criado contendo `DocumentChunkCollection` com lista de parents e childs.
- [ ] `__init__.py` atualizado como facade exportando os novos tipos.
**Verificação:**
- [ ] `uv run pytest tests/unit/test_chunk_value_objects.py -v`
**Dependências:** Nenhuma
**Arquivos prováveis:**
- `src/modules/knowledge/domain/value_objects/child_chunk.py`
- `src/modules/knowledge/domain/value_objects/parent_chunk.py`
- `src/modules/knowledge/domain/value_objects/document_chunk_collection.py`
- `src/modules/knowledge/domain/value_objects/__init__.py`
- `tests/unit/test_chunk_value_objects.py`
**Escopo estimado:** M (5 arquivos)

---

### Tarefa 2: Implementar Protocolos de Domínio (`IMarkdownChunker`, `IEmbeddingService`) e `DocumentChunkedEvent`
**Descrição:** Criar as abstrações de interface de particionamento e de serviço de embeddings assíncronos no domínio, e definir o evento de domínio `DocumentChunkedEvent`.
**Critérios de Aceite:**
- [ ] Arquivo `src/modules/knowledge/domain/interfaces/i_markdown_chunker.py` criado com método assíncrono `chunk(document_name: str, markdown_text: str) -> DocumentChunkCollection`.
- [ ] Arquivo `src/modules/knowledge/domain/interfaces/i_embedding_service.py` criado com métodos `embed_texts(texts, titles)` e `embed_query(query)`.
- [ ] Arquivo `src/modules/knowledge/domain/events/document_chunked_event.py` criado como `DomainEvent` contendo `document_id`, `total_parents`, `total_children` e `chunks_summary`.
- [ ] `__init__.py` em interfaces e events atualizados.
**Verificação:**
- [ ] `uv run pytest tests/unit/test_document_chunked_event.py -v`
**Dependências:** Tarefa 1
**Arquivos prováveis:**
- `src/modules/knowledge/domain/interfaces/i_markdown_chunker.py`
- `src/modules/knowledge/domain/interfaces/i_embedding_service.py`
- `src/modules/knowledge/domain/interfaces/__init__.py`
- `src/modules/knowledge/domain/events/document_chunked_event.py`
- `src/modules/knowledge/domain/events/__init__.py`
- `tests/unit/test_document_chunked_event.py`
**Escopo estimado:** M (6 arquivos)

---

## Checkpoint 1: Domínio e Contratos
- [ ] Testes unitários passando: `uv run pytest tests/unit/test_chunk_value_objects.py tests/unit/test_document_chunked_event.py`
- [ ] Checagem estrita de tipos: `uv run mypy src/modules/knowledge/domain`

---

## Fase 2: Chunker Estrutural Recursivo de Markdown

### Tarefa 3: Implementar `MarkdownParentChildChunker`
**Descrição:** Implementar o algoritmo structure-aware que decompõe Markdowns respeitando cabeçalhos (H1 a H6), isolando tabelas completas e blocos de código com cercas (```), subdividindo recursivamente seções que excedam 1.200 tokens em sub-parents com breadcrumbs contextuais e gerando child chunks (150-250 tokens com overlap).
**Critérios de Aceite:**
- [ ] Arquivo `src/modules/knowledge/infrastructure/chunking/markdown_parent_child_chunker.py` criado implementando `IMarkdownChunker`.
- [ ] Preservação integral e indivisível de tabelas Markdown e code blocks.
- [ ] Subdivisão recursiva de seções > 1200 tokens por parágrafos/listas com herança de breadcrumbs.
- [ ] Geração de child chunks menores (150-250 tokens) vinculados ao seu `parent_chunk_id`.
- [ ] Fallback resiliente para Markdowns sem cabeçalhos.
**Verificação:**
- [ ] `uv run pytest tests/unit/test_markdown_parent_child_chunker.py -v`
**Dependências:** Tarefa 2
**Arquivos prováveis:**
- `src/modules/knowledge/infrastructure/chunking/markdown_parent_child_chunker.py`
- `src/modules/knowledge/infrastructure/chunking/__init__.py`
- `tests/unit/test_markdown_parent_child_chunker.py`
**Escopo estimado:** S (3 arquivos)

---

## Checkpoint 2: Chunker Estrutural
- [ ] Testes do chunker cobrindo seções normais, seções gigantes, tabelas e código passando com 100% de sucesso.

---

## Fase 3: Substrato de Embeddings Gemini 2 & InMemory Adapter

### Tarefa 4: Implementar `InMemoryEmbeddingService` & `GeminiEmbeddingAdapter`
**Descrição:** Implementar o adaptador para a API Google Gemini (`gemini-embedding-2`) com formatação por prompt (`title: ... | text: ...` e `task: search result | query: ...`), suporte a MRL (768/512 dimensões), micro-batching de até 100 itens por chamada e resiliência a status HTTP 429 via Token Bucket e Exponential Backoff com Full Jitter. Implementar também o `InMemoryEmbeddingService` para testes determinísticos.
**Critérios de Aceite:**
- [ ] Arquivo `src/modules/knowledge/infrastructure/adapters/in_memory_embedding_service.py` criado implementando `IEmbeddingService`.
- [ ] Arquivo `src/modules/knowledge/infrastructure/adapters/gemini_embedding_adapter.py` criado implementando `IEmbeddingService` conectando à API do Gemini com cliente HTTP assíncrono (`httpx` / `google-genai`).
- [ ] Tratamento transparente de HTTP 429 com Exponential Backoff + Jitter.
- [ ] Testes unitários com simulação de 429 e validação de lotes.
**Verificação:**
- [ ] `uv run pytest tests/unit/test_gemini_embedding_adapter.py tests/unit/test_in_memory_embedding_service.py -v`
**Dependências:** Tarefa 2
**Arquivos prováveis:**
- `src/modules/knowledge/infrastructure/adapters/in_memory_embedding_service.py`
- `src/modules/knowledge/infrastructure/adapters/gemini_embedding_adapter.py`
- `src/modules/knowledge/infrastructure/adapters/__init__.py`
- `tests/unit/test_gemini_embedding_adapter.py`
- `tests/unit/test_in_memory_embedding_service.py`
**Escopo estimado:** M (5 arquivos)

---

## Checkpoint 3: Adaptadores de Embeddings
- [ ] Testes de embeddings passando: `uv run pytest tests/unit/test_gemini_embedding_adapter.py tests/unit/test_in_memory_embedding_service.py`

---

## Fase 4: Persistência de Chunks no PgVector & Extensão do IVectorStore

### Tarefa 5: Estender `IVectorStore`, `PgVectorStoreAdapter` e `InMemoryVectorStoreAdapter` para `document_chunks`
**Descrição:** Atualizar o contrato `IVectorStore` e os adaptadores `PgVectorStoreAdapter` e `InMemoryVectorStoreAdapter` para suportar inserção em batch de `ChildChunk`s com `parent_content` e busca semântica por similaridade de cosseno com suporte a filtros por `kb_id` e lista de `document_ids`.
**Critérios de Aceite:**
- [ ] Protocolo `IVectorStore` estendido com `store_document_chunks(kb_id, chunks)` e `search_similar_chunks(kb_id, query_embedding, top_k, document_ids)`.
- [ ] `PgVectorStoreAdapter` atualizado com schema DDL da tabela `document_chunks`, índice HNSW (`vector_cosine_ops`) e índice composto `(kb_id, document_id)`.
- [ ] `InMemoryVectorStoreAdapter` atualizado com cálculo de similaridade e filtros por `document_ids`.
**Verificação:**
- [ ] `uv run pytest tests/unit/test_pgvector_store_adapter.py tests/integration/test_pgvector_chunk_storage.py -v`
**Dependências:** Tarefa 1, Tarefa 2
**Arquivos prováveis:**
- `src/modules/knowledge/domain/interfaces/i_vector_store.py`
- `src/modules/knowledge/infrastructure/adapters/pgvector_store_adapter.py`
- `src/modules/knowledge/infrastructure/adapters/in_memory_vector_store_adapter.py`
- `tests/unit/test_pgvector_store_adapter.py`
- `tests/integration/test_pgvector_chunk_storage.py`
**Escopo estimado:** M (5 arquivos)

---

## Checkpoint 4: Persistência Vetorial
- [ ] Testes de persistência vetorial passando com mock e banco real: `uv run pytest tests/unit/test_pgvector_store_adapter.py tests/integration/test_pgvector_chunk_storage.py`

---

## Fase 5: Evolução da Saga de Ingestão e Container IoC

### Tarefa 6: Atualizar Aggregate `KnowledgeBaseAggregate`, Saga Coordinator e Container IoC
**Descrição:** Integrar o fluxo de chunking e embeddings na Saga coreografada `DocumentIngestionSagaCoordinator`, adicionando o método `mark_document_chunked(...)` no agregado e injetando o `IMarkdownChunker` e `IEmbeddingService` no container IoC da API Gateway.
**Critérios de Aceite:**
- [ ] `KnowledgeBaseAggregate` atualizado com `mark_document_chunked(...)` emitindo `DocumentChunkedEvent`.
- [ ] `DocumentIngestionSagaCoordinator` atualizado para escutar `DocumentParsedToMarkdownEvent` ➔ executar chunking ➔ escutar `DocumentChunkedEvent` ➔ gerar embeddings e persistir chunks ➔ extrair grafos ontológicos.
- [ ] `src/api_gateway/container.py` configurado para instanciar e injetar os novos adaptadores.
- [ ] Testes da Saga e testes E2E atualizados e passando.
**Verificação:**
- [ ] `uv run pytest tests/unit/test_knowledge_module.py tests/integration/test_document_ingestion_saga_coordinator.py -v`
**Dependências:** Tarefa 3, Tarefa 4, Tarefa 5
**Arquivos prováveis:**
- `src/modules/knowledge/domain/aggregates/knowledge_base_aggregate.py`
- `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`
- `src/api_gateway/container.py`
- `tests/unit/test_knowledge_module.py`
- `tests/integration/test_document_ingestion_saga_coordinator.py`
**Escopo estimado:** M (5 arquivos)

---

## Checkpoint Final: Validação de Qualidade Global
- [ ] Execução completa do gate oficial: `make pre-commit`
- [ ] 100% dos testes unitários e de integração passando.
- [ ] Zero erros de linter (Ruff) e Mypy em modo estrito (`strict = true`).
