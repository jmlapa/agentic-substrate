# Idea: Unified FalkorDB Hybrid GraphRAG & Structural Node Ingestion

## Problem Statement
Como podemos indexar documentos extensos e complexos (ex: Constituição Federal de 250 páginas) de forma escalável e sem gargalos de contexto de LLM, unificando a busca vetorial de alta precisão e a travessia de grafos ontológicos em um único banco de leitura?

---

## Recommended Direction

Unificar o **Read Model de Conhecimento** diretamente no **FalkorDB**, aproveitando suas capacidades nativas de **Vector Indexing (`db.idx.vector`)** e **OpenCypher Graph Traversal**. 

O PostgreSQL permanece exclusivamente como **Event Store transacional** e persistência de agregados/metadados.

### 1. Nova Topologia do Grafo no FalkorDB
O grafo passa a refletir tanto a **hierarquia estrutural do documento** quanto os **conceitos ontológicos extraídos**:

```text
(:Document {id, name, created_at})
    │
    ▼ [:CONTAINS_PARENT]
(:ParentChunk {id, header_path, content, token_count}) ──[:MENTIONS]──> (:OntologicalEntity {type, name, ...})
    │                                                                           ▲
    ▼ [:CONTAINS_CHILD]                                                        │
(:ChildChunk {id, chunk_index, embedding: [768d]}) ─────────────────────────────┘
```

### 2. Pipeline de Ingestão por Parent Chunk
Em vez de passar o documento completo para a LLM, a Saga de ingestão opera em fatias delimitadas:
1. **Parsing:** `MarkItDown` converte o documento (PDF, DOCX, TXT) para Markdown localmente.
2. **Chunking Estrutural:** `MarkdownParentChildChunker` particiona em `ParentChunks` (~1.000 tokens) e `ChildChunks` (~200 tokens).
3. **Embeddings:** `GeminiEmbeddingAdapter` gera vetores (768 dimensões com MRL) para os `ChildChunks`.
4. **Extração Ontológica em Lote:** A LLM recebe cada `ParentChunk` individual com o schema Pydantic da ontologia, garantindo atenção máxima sem estouro de contexto.
5. **Persistência Unificada:** O `FalkorDbGraphStoreAdapter` cria os nós `Document`, `ParentChunk`, `ChildChunk` (com índice vetorial) e as entidades ontológicas conectadas via Cypher `MERGE`.

### 3. Busca Híbrida em Query Única (Cypher + Vector)
A consulta híbrida não necessita de fusão manual em memória no Python. Uma única query Cypher no FalkorDB realiza a busca por similaridade e expande o subgrafo relacional:

```cypher
// Busca vetorial nos Child Chunks
CALL db.idx.vector.queryNodes('ChildChunk', 'embedding', $top_k, $query_embedding) 
YIELD node AS child, score

// Navegação direta para o Parent Chunk e entidades conceituais
MATCH (parent:ParentChunk)-[:CONTAINS_CHILD]->(child)
OPTIONAL MATCH (parent)-[:MENTIONS]->(entity)

RETURN parent.id AS parent_id,
       parent.header_path AS header_path,
       parent.content AS parent_content,
       collect(DISTINCT {type: labels(entity)[0], properties: properties(entity)}) AS related_entities,
       max(score) AS relevance_score
ORDER BY relevance_score DESC
```

---

## Key Assumptions to Validate
- [ ] **Desempenho Vetorial no FalkorDB:** Validar a latência do índice vetorial HNSW em memória no FalkorDB para bases com milhares de chunks.
- [ ] **Concorrência de MERGE no FalkorDB:** Testar a ingestão concorrente de subgrafos paralelos por múltiplos workers assíncronos.
- [ ] **Consumo de Memória:** Mensurar o footprint de RAM do FalkorDB para documentos densos com embeddings de 768 dimensões.

---

## MVP Scope

### In Scope
1. **Modelagem de Nós Estruturais:** Inclusão de `ParentChunk` e `ChildChunk` como tipos de nós formais no adapter do FalkorDB.
2. **Índice Vetorial no FalkorDB:** Criação automática de `VECTOR INDEX FOR (c:ChildChunk) ON (c.embedding)` por Knowledge Base.
3. **Extração por Parent Chunk na Saga:** Atualização do `DocumentIngestionSagaCoordinator` para enviar `ParentChunks` individuais para o `StructuredPydanticGraphExtractor`.
4. **Query Híbrida Unificada no Use Case:** Implementação do `QueryKnowledgeUseCase` executando busca vetorial com expansão relacional em uma única chamada Cypher.

### Out of Scope (Not Doing - and Why)
- **Tabelas de Chunks Vetoriais no PostgreSQL (`document_chunks`):** Removido do caminho de consulta para eliminar redundância de dados e evitar o problema de sincronização entre dois bancos de leitura. O Postgres foca em Event Sourcing e dados relacionais puros.
- **Rerankers de Terceiros (ex: Cohere Rerank):** Não utilizaremos rerankers externos no MVP; o ranking será baseado na similaridade de cosseno combinada com conectividade do grafo no próprio FalkorDB.
- **Sanitizers Específicos por Tipo de Documento:** Não criaremos regras de regex manuais para leis ou formatos específicos; o chunker opera de forma universal baseando-se em parágrafos e cabeçalhos Markdown.

---

## Open Questions
1. Qual deve ser o threshold padrão de similaridade de cosseno na chamada `db.idx.vector.queryNodes` do FalkorDB para filtrar ruídos antes de expandir o grafo?
2. Em bases com centenas de documentos compartilhando a mesma ontologia, devemos permitir busca híbrida cross-document filtrada por tags/metadados da Knowledge Base?
