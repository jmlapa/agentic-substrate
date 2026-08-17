# Plano de Implementação: Markdown Parent-Child Chunking & Gemini Embedding 2 (Marco 1.6)

## Visão Geral
Implementar no módulo `knowledge` do **Agentic Substrate** a capacidade completa de particionamento hierárquico e estrutural de Markdowns (`MarkdownParentChildChunker`), geração assíncrona de embeddings via Google Gemini (`gemini-embedding-2`), persistência particionada com índice HNSW no PostgreSQL (`pgvector`) na tabela `document_chunks` e orquestração integrada na Saga coreografada de ingestão (`DocumentIngestionSagaCoordinator`) com o novo evento `DocumentChunkedEvent`.

---

## Decisões Arquiteturais e Escolhas Técnicas

1. **Recursive Markdown Structure-Aware + Parent-Child Chunker:**
   - **Abordagem:** Análise estrutural de Markdown baseada em blocos. Identifica cabeçalhos (H1 a H6), preserva tabelas completas e blocos de código com cercas (```) sem quebras intermediárias.
   - **Parent Chunks:** Delimitados por seções de cabeçalhos. Se uma seção exceder o orçamento (1.200 tokens), é subdividida recursivamente por limites naturais (`\n\n` parágrafos, listas e blocos atômicos). Cada Parent Chunk recebe um `header_path` contextual (ex: `[Doc: Nome] > # Seção > ## Subseção (Parte N)`).
   - **Child Chunks:** Subdivisão do Parent em blocos menores (150 a 250 tokens) com overlap semântico (frases completas). Apenas os Child Chunks são vetorizados.
   - **Recuperação:** O match semântico no Child Chunk resgata o Parent Chunk completo para compor o contexto do LLM.

2. **Substrato de Embeddings Gemini 2 (`IEmbeddingService`):**
   - **Modelo:** `gemini-embedding-2` via API oficial (Google GenAI / REST assíncrono).
   - **Instruções de Tarefa no Prompt:**
     - Indexação de Chunks: `title: {doc_title} | text: {breadcrumb}\n\n{content}`
     - Consulta (Query): `task: search result | query: {query}`
   - **MRL (Matryoshka Representation Learning):** `output_dimensionality = 768` (ou 512), aproveitando a auto-normalização nativa do modelo para distância de cosseno (`<=>`).
   - **Micro-Batching:** Divisão assíncrona de lotes em até 100 itens por chamada HTTP.
   - **Resiliência a 429:** Async Token Bucket Rate Limiter + Exponential Backoff com Full Jitter para tolerância a `ResourceExhausted` (HTTP 429).

3. **Armazenamento Vetorial no PostgreSQL (`document_chunks`):**
   - **Tabela:** `document_chunks` com colunas `id`, `kb_id`, `document_id`, `parent_chunk_id`, `chunk_index`, `header_path`, `content`, `parent_content`, `embedding vector(768)`, `metadata jsonb`.
   - **Índices:** Índice HNSW sobre o vetor (`vector_cosine_ops`) e índice B-Tree composto `(kb_id, document_id)` para permitir buscas filtradas ultra-rápidas durante o roteamento pelo grafo ontológico.

4. **Saga Coreografada com 6 Passos:**
   - Fluxo: `DocumentAttachedEvent` ➔ `DocumentStoredEvent` ➔ `DocumentParsedToMarkdownEvent` ➔ `DocumentChunkedEvent` ➔ `GraphExtractedFromDocumentEvent` ➔ `DocumentKnowledgeIndexedEvent`.

---

## Estrutura do Grafo de Dependências

```
Domain Value Objects (ParentChunk, ChildChunk, DocumentChunkCollection)
    │
    ├── Domain Protocols & Events (IMarkdownChunker, IEmbeddingService, DocumentChunkedEvent)
    │       │
    │       ├── Infrastructure Chunker: MarkdownParentChildChunker
    │       │
    │       ├── Infrastructure Embeddings: GeminiEmbeddingAdapter & InMemoryEmbeddingService
    │       │
    │       └── Infrastructure Vector Store: PgVectorStoreAdapter (document_chunks table)
    │               │
    │               └── Application Saga: DocumentIngestionSagaCoordinator & Container IoC
```

---

## Fases de Implementação

### Fase 1: Primitivas de Domínio, Value Objects, Protocolos e Eventos
- Criar `ParentChunk`, `ChildChunk`, `DocumentChunkCollection` em `domain/value_objects/`.
- Criar `IMarkdownChunker` e `IEmbeddingService` em `domain/interfaces/`.
- Criar `DocumentChunkedEvent` em `domain/events/`.

### Checkpoint 1: Domínio Puro & Eventos
- [ ] Testes unitários de Value Objects e Eventos passando (`uv run pytest tests/unit/test_chunk_value_objects.py tests/unit/test_document_chunked_event.py`).
- [ ] Validação com `uv run mypy src tests`.

### Fase 2: Chunker Estrutural Recursivo de Markdown
- Implementar `MarkdownParentChildChunker` em `infrastructure/chunking/`.
- Cobrir casos de teste: seções normais, seções gigantes (> 1200 tokens), documentos sem headers, isolamento de tabelas Markdown e blocos de código.

### Checkpoint 2: Chunker Estrutural
- [ ] Testes unitários do chunker passando com 100% de cobertura (`uv run pytest tests/unit/test_markdown_parent_child_chunker.py`).

### Fase 3: Substrato de Embeddings Gemini 2 & InMemory Adapter
- Implementar `InMemoryEmbeddingService` para execução determinística em testes.
- Implementar `GeminiEmbeddingAdapter` com formatação por prompt, MRL, micro-batches de 100 e retry policy com jitter para HTTP 429.

### Checkpoint 3: Adaptadores de Embeddings
- [ ] Testes unitários do adaptador Gemini e InMemory passando (`uv run pytest tests/unit/test_gemini_embedding_adapter.py tests/unit/test_in_memory_embedding_service.py`).

### Fase 4: Persistência de Chunks no PgVector & Extensão do IVectorStore
- Estender `IVectorStore`, `PgVectorStoreAdapter` e `InMemoryVectorStoreAdapter` com `store_document_chunks` e `search_similar_chunks` (com filtros por `document_ids`).
- Adicionar DDL da tabela `document_chunks` e índice HNSW no Postgres.

### Checkpoint 4: Persistência Vetorial de Chunks
- [ ] Testes unitários e de integração de persistência vetorial de chunks passando (`uv run pytest tests/unit/test_pgvector_store_adapter.py tests/integration/test_pgvector_chunk_storage.py`).

### Fase 5: Evolução da Saga de Ingestão e Container IoC
- Atualizar `KnowledgeBaseAggregate` com o método `mark_document_chunked(...)`.
- Atualizar `DocumentIngestionSagaCoordinator` para orquestrar o evento `DocumentChunkedEvent`, geração de embeddings e extração de grafos com rastreabilidade de chunks.
- Atualizar `src/api_gateway/container.py` para injetar o chunker e embedding service.

### Checkpoint Final: Validação Ponta a Ponta
- [ ] Teste de integração da Saga completa (`tests/unit/test_knowledge_module.py` e `tests/integration/test_document_ingestion_saga_coordinator.py`).
- [ ] Execução com sucesso do gate oficial `make pre-commit`.

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Rate limit da API Gemini (HTTP 429) em cargas de ingestão pesadas | Alto | Implementar Token Bucket limiter e retry exponencial assíncrono com Full Jitter no adaptador, fatiando em micro-batches de no máximo 100 chunks. |
| Quebra de formatação de tabelas Markdown durante o particionamento | Alto | Implementar parser que trata blocos de tabelas (`\| col \|`) e blocos cercados de código (```) como nós indivisíveis no AST/regex do chunker. |
| Incompatibilidade de versão em eventos anteriores da Saga | Médio | Manter os eventos existentes retrocompatíveis e encadear o novo evento `DocumentChunkedEvent` de forma fluida. |
