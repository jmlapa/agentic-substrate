# Spec: Markdown Parent-Child Chunking & Gemini Embedding 2 Substrate

## Objective
Implementar um pipeline robusto de particionamento hierárquico de Markdown (`MarkdownParentChildChunker`) e geração assíncrona de embeddings via Google Gemini (`gemini-embedding-2`), integrando os vetores de texto e entidades ontológicas no PostgreSQL com `pgvector` e amarrando a proveniência dos chunks na Saga Coreografada de ingestão do Knowledge Substrate.

### User Stories & Comportamento
1. **Particionamento Estrutural com Fallback Recursivo:** Ao receber um Markdown bruto (gerado pelo MarkItDown), o sistema decompõe o documento em **Parent Chunks** (seções delimitadas por H1-H6 com limite de até 1.200 tokens) e **Child Chunks** (150 a 250 tokens com overlap semântico). Tabelas e blocos de código são mantidos indivisíveis.
2. **Embeddings Gemini 2 com MRL e Rate Limiting:** A interface `IEmbeddingService` e o adaptador `GeminiEmbeddingAdapter` comunicam com o modelo `gemini-embedding-2` utilizando formatação por prompt (`title: ... | text: ...` e `task: search result | query: ...`), dimensões configuráveis via MRL (768 ou 512 auto-normalizados), batching de até 100 itens por chamada e resiliência com Exponential Backoff + Jitter para tratamento de HTTP 429.
3. **Persistência Vetorial e Roteamento GraphRAG:** O `PgVectorStoreAdapter` armazena os Child Chunks na tabela `document_chunks` vinculados ao seu `parent_content` e `metadata`. Na busca, queries vetoriais podem ser filtradas por `document_id`s e metadados identificados durante a travessia de subgrafos no FalkorDB.
4. **Saga Coreografada Atualizada:** O pipeline de ingestão incorpora o evento `DocumentChunkedEvent`, garantindo rastreabilidade do ciclo de vida: `DocumentStoredEvent` ➔ `DocumentParsedToMarkdownEvent` ➔ `DocumentChunkedEvent` ➔ `GraphExtractedFromDocumentEvent` ➔ `DocumentKnowledgeIndexedEvent`.

---

## Tech Stack
- **Linguagem & Runtime:** Python 3.12+
- **Embedding Provider:** Google GenAI / Gemini API (`gemini-embedding-2`)
- **Gerenciador de Dependências:** `uv` (`pyproject.toml`)
- **Vector Store & Relacional:** PostgreSQL 16 + `pgvector` (`vector(768)`) via driver `asyncpg`
- **Validação & Schemas:** Pydantic v2
- **Qualidade & Tipagem:** Ruff (linter/formatador), Mypy (`strict = true`), Pytest com `pytest-asyncio`

---

## Commands
```bash
# Executar todos os testes unitários e de integração
uv run pytest --cov=src --cov-report=term-missing -v

# Linter e Formatação
uv run ruff check .
uv run ruff format --check .

# Checagem de tipos estrita (Zero Any implícito)
uv run mypy src tests

# Gate oficial de qualidade pré-commit
make pre-commit
```

---

## Project Structure (Single Class per File)
```
src/modules/knowledge/
├── domain/
│   ├── events/
│   │   └── document_chunked_event.py          # DomainEvent emitido após o particionamento
│   ├── interfaces/
│   │   ├── i_markdown_chunker.py              # Protocol do particionador estrutural
│   │   ├── i_embedding_service.py             # Protocol do serviço assíncrono de embeddings
│   │   └── i_vector_store.py                  # Protocol estendido com métodos de document chunks
│   └── value_objects/
│       ├── child_chunk.py                     # Value Object de Child Chunk (texto, embedding, parent_id, breadcrumb)
│       ├── parent_chunk.py                    # Value Object de Parent Chunk (seção íntegra, cabeçalhos, tokens)
│       └── document_chunk_collection.py       # Aggregate/VO agrupando parents e childs do documento
├── infrastructure/
│   ├── adapters/
│   │   ├── gemini_embedding_adapter.py        # Adaptador Gemini 2 com MRL, Batching e Retry 429
│   │   ├── in_memory_embedding_service.py     # Adaptador in-memory determinístico para testes
│   │   └── pgvector_store_adapter.py          # Extensão para tabela document_chunks e índices HNSW
│   └── chunking/
│       └── markdown_parent_child_chunker.py   # Implementação recursive Markdown structure-aware
└── application/
    └── sagas/
        └── document_ingestion_saga_coordinator.py # Orquestração atualizada com DocumentChunkedEvent
```

---

## Code Style & Architecture Conventions

### 1. Single Class per File & Type Annotations
Cada classe, protocolo ou value object reside em seu próprio arquivo isolado, com tipagem 100% estrita e exports em `__init__.py`.

```python
# src/modules/knowledge/domain/value_objects/child_chunk.py
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChildChunk:
    id: str
    parent_chunk_id: str
    chunk_index: int
    header_path: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 2. Interface de Embeddings Assíncrona com Batching
```python
# src/modules/knowledge/domain/interfaces/i_embedding_service.py
from typing import Protocol, runtime_checkable


@runtime_checkable
class IEmbeddingService(Protocol):
    async def embed_texts(
        self,
        texts: list[str],
        titles: list[str] | None = None,
    ) -> list[list[float]]: ...

    async def embed_query(self, query: str) -> list[float]: ...
```

---

## Testing Strategy
- **Testes Unitários:**
  - `tests/unit/test_markdown_parent_child_chunker.py`: Testar isolamento de seções H1/H2/H3, tabelas Markdown, blocos de código com cercas (```), subdivisão recursiva de seções gigantes (> 1200 tokens) e documentos sem cabeçalhos.
  - `tests/unit/test_gemini_embedding_adapter.py`: Testar formatação de prompts (`title | text` e `task: search result | query`), batching em lotes de 100, MRL (dimensão 768) e comportamento de retry com backoff ao receber HTTP 429 simulado.
  - `tests/unit/test_document_chunked_event.py`: Testar imutabilidade e integridade do evento de domínio.
- **Testes de Integração:**
  - `tests/integration/test_pgvector_chunk_storage.py`: Testar criação de schema `document_chunks`, inserção em lote de vetores e busca semântica por similaridade de cosseno com filtros de metadados.
  - `tests/integration/test_document_ingestion_saga_coordinator.py`: Testar o fluxo E2E completo com parsing MarkItDown ➔ Chunking ➔ Embeddings ➔ Extração Ontológica ➔ Persistência Híbrida.

---

## Boundaries
- **Always:**
  - Respeitar estritamente a regra de 1 Classe / 1 Interface / 1 DTO por arquivo.
  - Operar com `mypy --strict` sem nenhum `# type: ignore` desnecessário.
  - Formatar prompts do Gemini Embedding 2 conforme especificação oficial do Google (`title: ... | text: ...` e `task: search result | query: ...`).
  - Tratar HTTP 429 com exponential backoff e full jitter no adaptador de embeddings.
  - Executar `make pre-commit` para validação antes de qualquer commit.
- **Ask first:**
  - Alteração de dimensões padrão de vetores no PostgreSQL (ex: migrar de 768 para 512).
  - Adição de novos modelos ou provedores de embedding proprietários externos.
- **Never:**
  - Quebrar tabelas Markdown ou blocos de código ao meio durante o chunking sem respeitar os limites de bloco.
  - Vetorizar o Markdown inteiro como um bloco único monolítico.
  - Utilizar chamadas de rede síncronas bloqueantes dentro da camada assíncrona.

---

## Success Criteria & Capacidades Validadas
1. **Hierarquia e Integridade:** O `MarkdownParentChildChunker` divide markdowns complexos preservando tabelas e blocos de código inteiros, gerando parents (<= 1.200 tokens) e childs (150-250 tokens) com breadcrumbs contextuais.
2. **Resiliência a Rate Limit:** O `GeminiEmbeddingAdapter` processa lotes de centenas de chunks divididos em micro-batches de até 100 itens, recuperando-se transparentemente de erros 429 via retry exponencial com jitter.
3. **Persistência Vetorial Filtrável:** O `PgVectorStoreAdapter` persiste chunks na tabela `document_chunks` com índice HNSW e realiza buscas de similaridade de cosseno com restrição opcional por lista de `document_id`s.
4. **Saga Integrada:** A ingestão coreografada transiciona perfeitamente através de `DocumentChunkedEvent` sem quebra de compatibilidade com os eventos existentes.
5. **Zero Erros:** 100% dos testes unitários e de integração passando, com cobertura de código e validação completa no `make pre-commit`.
