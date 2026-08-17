# Refinamento: Markdown Structure-Aware Parent-Child Chunking & Gemini Embeddings Substrate

## Problem Statement
Como poderíamos particionar documentos Markdown extensos gerados pelo MarkItDown preservando integridade estrutural (tabelas, códigos, hierarquia H1-H6 com fallback recursivo para seções longas) e vetorizá-los via Google Gemini `gemini-embedding-2` (com MRL 768/512 dims, auto-normalização, task-formatting e batching com resiliência a 429), integrando os chunks bidirecionalmente com o grafo ontológico para busca híbrida de alta precisão?

## Recommended Direction
1. **Recursive Markdown Structure-Aware + Parent-Child Chunker:**
   - **Parent Chunks:** Seções delimitadas por cabeçalhos Markdown (H1-H6). Se uma seção exceder o orçamento máximo (ex: 1.200 tokens), é subdividida recursivamente por limites naturais (`\n\n` parágrafos, listas, tabelas e code blocks indivisíveis) em sub-parents de até 1.200 tokens. Cada parent mantém seu breadcrumb hierárquico (`[Doc: Nome] > # Seção > ## Subseção (Parte N)`).
   - **Child Chunks:** Subdivisão de cada parent em pequenos trechos de 150 a 250 tokens com overlap semântico (frases). Cada child herda o breadcrumb contextual completo. Apenas os child chunks são vetorizados no Gemini para garantir máxima acurácia na similaridade de cosseno.
   - **Geração de Resposta:** Na busca semântica, o match em um child chunk recupera seu respectivo parent chunk íntegro (com tabelas e código completos) para compor o prompt do LLM.

2. **Substrato de Embeddings Gemini (`IEmbeddingService`):**
   - Interface assíncrona pura no domínio (`IEmbeddingService`) para desacoplar a geração de embeddings do storage.
   - Adaptador `GeminiEmbeddingAdapter` comunicando com o modelo `gemini-embedding-2` via API oficial (REST/SDK) com suporte a:
     - Formatação de tarefas via prompt instruction (`title: {doc_title} | text: {content}` para indexação; `task: search result | query: {query}` para buscas).
     - Matryoshka Representation Learning (MRL) com `output_dimensionality=768` (ou 512), aproveitando a auto-normalização nativa do `gemini-embedding-2`.
     - Micro-batching assíncrono (até 100 `Content` items por request).
     - Token bucket rate limiter e retry policy assíncrona com Exponential Backoff + Full Jitter para tolerância a HTTP 429 (ResourceExhausted).

3. **Persistência Vetorial no PostgreSQL (`document_chunks`):**
   - Tabela `document_chunks` no PostgreSQL com índice HNSW sobre `vector(768)` isolada por `kb_id`, armazenando `id`, `document_id`, `parent_chunk_id`, `chunk_index`, `header_path`, `content`, `parent_content`, `embedding` e `metadata`.
   - Extensão do `PgVectorStoreAdapter` para indexação em lote e busca híbrida/filtrada por `document_id` e metadados.

4. **Integração com o Grafo Ontológico (Proveniência & Roteamento):**
   - Entidades e nós extraídos no `IGraphExtractor` guardam referência aos `chunk_ids` de origem (`provenance_chunks`).
   - A busca GraphRAG utiliza o subgrafo descoberto para filtrar os `document_id`s de interesse e executa a busca vetorial nos child chunks desses documentos específicos, resgatando os parent chunks correspondentes para o LLM.

## Key Assumptions to Validate
- [ ] O `gemini-embedding-2` com MRL em 768 ou 512 dimensões mantém recall semântico superior a 98% no PostgreSQL com `pgvector` e índice HNSW.
- [ ] O algoritmo recursivo de chunking isola tabelas e code blocks sem quebras internas de sintaxe.
- [ ] O mecanismo de retry com jitter recupera com sucesso requisições atingidas por rate limit 429 durante ingestão de documentos volumosos.

## MVP Scope
- Criação de `IEmbeddingService` e `GeminiEmbeddingAdapter` com controle de taxa e retry.
- Criação de `MarkdownParentChildChunker` (Single Class per File) com extração de breadcrumbs e isolamento de tabelas/código.
- Criação da entidade/value objects de chunk (`DocumentChunk`, `ParentChunk`, `ChildChunk`).
- Criação da tabela `document_chunks` e métodos correspondentes no `PgVectorStoreAdapter` e `IVectorStore`.
- Evolução da Saga `DocumentIngestionSagaCoordinator` para incluir o evento `DocumentChunkedEvent` no pipeline de ingestão.

## Not Doing (and Why)
- **Local Embedding Fallback (FastEmbed/ONNX):** Descartado para manter o substrato leve e focado no `gemini-embedding-2` via API com resiliência a 429.
- **Quebra no meio de tabelas Markdown:** Proibido dividir tabelas entre chunks diferentes para não corromper dados tabulares.
- **Vetorização do documento inteiro:** Descartado para evitar diluição semântica e estouro de contexto de LLM.

## Open Questions
- Nenhum bloqueador identificado no momento da especificação.
