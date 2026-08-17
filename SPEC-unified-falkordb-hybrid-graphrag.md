# Spec: Unified FalkorDB Hybrid GraphRAG & Structural Node Ingestion

## Objective
Unificar o modelo de leitura e busca do Knowledge Substrate diretamente no **FalkorDB**, transformando o grafo em uma estrutura híbrida contendo tanto a **espinha dorsal estrutural do documento** (`Document` ➔ `ParentChunk` ➔ `ChildChunk`) quanto as **entidades conceituais ontológicas** (`Mentions`). 
A busca híbrida (similaridade de cosseno vetorial + expansão de subgrafo) é executada em uma **única query Cypher** utilizando o motor vetorial nativo do FalkorDB (`db.idx.vector.queryNodes`), eliminando o acoplamento de leitura ao PostgreSQL e permitindo indexar documentos extensos (ex: PDFs legislativos de 250 páginas) com extração em lotes paralelos por `ParentChunk`.

---

## User Stories & Comportamento Esperado
1. **Modelagem de Grafo Estrutural + Ontológico:** Ao processar um documento, o `FalkorDbGraphStoreAdapter` cria e indexa:
   - `(:Document {id, kb_id, name, total_parents, total_children})`
   - `(:ParentChunk {id, kb_id, document_id, header_path, content, token_count})`
   - `(:ChildChunk {id, kb_id, parent_chunk_id, chunk_index, content, embedding})`
   - Índice vetorial HNSW: `VECTOR INDEX FOR (c:ChildChunk) ON (c.embedding)` com dimensão 768 e similaridade de cosseno.
2. **Ingestão Resiliente por Parent Chunk na Saga:** O `DocumentIngestionSagaCoordinator` deixa de passar o texto integral de documentos longos para o `StructuredPydanticGraphExtractor`. Em vez disso, o extrator é executado em paralelo/batch para cada `ParentChunk` (~1.000 tokens), conectando as entidades ontológicas ao respectivo `ParentChunk` via arestas `[:MENTIONS]`.
3. **Query Híbrida Unificada em Cypher:** O `QueryKnowledgeUseCase` recebe uma consulta do usuário, obtém o embedding via `IEmbeddingService`, e executa uma query Cypher única no `IGraphStore` que:
   - Realiza busca aproximada de vizinhos mais próximos (KNN) nos nós `ChildChunk`.
   - Recupera os `ParentChunk`s de maior relevância desduplicados.
   - Expande e agrupa as entidades ontológicas conectadas (`[:MENTIONS]`).
   - Retorna um payload consolidado com o texto íntegro dos pais, entidades relacionadas e score semântico.
4. **Papel Estrito do PostgreSQL:** O PostgreSQL permanece como Event Store imutável (`events`) e persistência de agregados de Knowledge Base.

---

## Tech Stack
- **Linguagem & Runtime:** Python 3.12+
- **Graph & Vector Engine:** FalkorDB (via driver `falkordb` e sintaxe OpenCypher)
- **Embeddings:** Google GenAI Gemini Embedding 2 (`gemini-embedding-2`, dimensão 768)
- **Parser & Chunker:** `MarkItDown` (Microsoft) + `MarkdownParentChildChunker`
- **Validação & Ontologia Dinâmica:** Pydantic v2
- **Qualidade & Tipagem:** Ruff (linter/formatador), Mypy (`strict = true`), Pytest com `pytest-asyncio`

---

## Commands
```bash
# Executar todos os testes unitários e de integração
uv run pytest --cov=src --cov-report=term-missing -v

# Linter e Formatação
uv run ruff check .
uv run ruff format --check .

# Checagem estrita de tipos
uv run mypy src tests

# Gate oficial de qualidade
make pre-commit
```

---

## Project Structure (Single Class per File)
```
src/modules/knowledge/
├── domain/
│   ├── interfaces/
│   │   ├── i_graph_store.py                     # Atualizado com métodos de ingestão estrutural e hybrid search
│   │   ├── i_vector_store.py                    # Mantido para abstrações vetoriais puras
│   │   ├── i_graph_extractor.py                 # Interface de extração ontológica
│   │   └── i_embedding_service.py               # Interface de geração de embeddings
│   └── value_objects/
│       ├── hybrid_search_result.py              # Value Object com ParentChunk + Entidades + Score
│       ├── structural_graph_document.py         # Value Object representando documento e chunks no grafo
│       └── extracted_graph.py                   # Value Object com nós e arestas ontológicas
├── infrastructure/
│   ├── adapters/
│   │   ├── falkordb_graph_store_adapter.py      # Adaptador estendido com Vector Index, Chunks e Hybrid Query
│   │   ├── in_memory_graph_store.py             # Adaptador in-memory atualizado para testes unitários
│   │   └── gemini_embedding_adapter.py          # Adaptador de embeddings Gemini
│   └── extractors/
│       └── structured_pydantic_graph_extractor.py # Extrator ontológico Pydantic em batch
└── application/
    ├── sagas/
    │   └── document_ingestion_saga_coordinator.py # Orquestrador com extração por ParentChunk
    └── use_cases/
        └── query_knowledge/
            ├── query_knowledge_request.py       # DTO Request com query e top_k
            ├── query_knowledge_response.py      # DTO Response com HybridSearchResult
            └── query_knowledge_use_case.py      # Caso de uso orquestrando embedding + FalkorDB Hybrid Search
```

---

## Code Style & Architecture Conventions

### 1. Single Class per File & Type Annotations
Cada entidade, value object, interface e caso de uso reside estritamente em seu próprio arquivo com tipagem Mypy estrita (`strict = true`).

```python
# src/modules/knowledge/domain/value_objects/hybrid_search_result.py
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HybridSearchResult:
    parent_chunk_id: str
    header_path: str
    parent_content: str
    relevance_score: float
    related_entities: list[dict[str, Any]] = field(default_factory=list)
```

### 2. Query Híbrida Cypher no FalkorDB
```python
# Trecho de execução no falkordb_graph_store_adapter.py
query = """
CALL db.idx.vector.queryNodes('ChildChunk', 'embedding', $top_k, $query_vec)
YIELD node AS child, score
MATCH (parent:ParentChunk)-[:CONTAINS_CHILD]->(child)
OPTIONAL MATCH (parent)-[:MENTIONS]->(entity)
RETURN parent.id AS parent_id,
       parent.header_path AS header_path,
       parent.content AS parent_content,
       collect(DISTINCT {type: labels(entity)[0], properties: properties(entity)}) AS related_entities,
       max(score) AS relevance_score
ORDER BY relevance_score DESC
"""
```

---

## Testing Strategy
- **Unit Tests:**
  - `tests/unit/test_falkordb_graph_store_adapter.py`: Mock do driver `falkordb` para validação da sintaxe Cypher, criação de índices vetoriais e montagem de nós estruturais.
  - `tests/unit/test_query_knowledge_use_case.py`: Teste unitário do caso de uso híbrido com `InMemoryGraphStore` e `InMemoryEmbeddingService`.
  - `tests/unit/test_document_ingestion_saga_coordinator.py`: Validação do fluxo de ingestão particionado por `ParentChunk`.
- **Integration Tests:**
  - `tests/integration/test_falkordb_hybrid_search_integration.py`: Teste com container real do FalkorDB (`docker-compose`) validando indexação vetorial nativa e travessia OpenCypher.

---

## Boundaries
- **Always:**
  - Executar `make pre-commit` antes de qualquer entrega.
  - Manter 1 classe por arquivo em todas as camadas.
  - Tratar fluxos com `Result[T, E]` e checagens explícitas `if isinstance(res, Err)`.
- **Ask first:**
  - Alterações no schema de eventos do Event Sourcing (`DocumentChunkedEvent`, etc.).
  - Remoção de tabelas legadas do PostgreSQL.
- **Never:**
  - Usar `# type: ignore` sem justificativa formal.
  - Deixar a Saga passar o documento integral de 250 páginas para a LLM de uma só vez.

---

## Success Criteria
- [ ] O FalkorDB cria e gerencia o índice vetorial `VECTOR INDEX FOR (c:ChildChunk) ON (c.embedding)`.
- [ ] A Saga processa cada `ParentChunk` individualmente na extração de grafos com a LLM.
- [ ] O `QueryKnowledgeUseCase` retorna resultados enriquecidos com `parent_content` e `related_entities` em uma única chamada de subgrafo.
- [ ] 100% de testes unitários e de integração passando com cobertura.
- [ ] Zero erros no `make pre-commit` (Mypy strict, Ruff linter, Ruff format).
