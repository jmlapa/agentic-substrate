# Spec: Universal Structure-Tolerant Markdown Parent-Child Chunker

## Objective
Implementar um particionador hierárquico universal e determinístico para textos em Markdown (`StructureTolerantMarkdownChunker`), agnóstico ao domínio do documento (leis, relatórios financeiros, manuais de TI com código, artigos acadêmicos com tabelas).
O particionador não depende da presença ou consistência de árvores de cabeçalhos Markdown (`H1` a `H6`). Em vez disso, opera como um **Lexer de Blocos Atômicos Indivisíveis** seguido por um **Empacotador Guloso com Sizing Estrito**, garantindo **Parent Chunks** uniformes (800 a 1.200 tokens) e **Child Chunks** de alta resolução (150 a 250 tokens com 30 tokens de overlap), preservando a integridade sintática de tabelas, blocos de código e parágrafos.

---

### User Stories & Comportamentos Esperados
1. **Preservação Determinística de Blocos Atômicos:** O chunker identifica elementos sintáticos indivisíveis:
   - Blocos de código cercados (```` ```...``` ````).
   - Tabelas Markdown completas (`| col1 | col2 | ...`).
   - Parágrafos de texto coesos delimitados por quebras duplas (`\n\n`).
   - Citações em bloco (`> ...`) e itens de lista.
   Nenhum desses blocos é dividido no meio durante o empacotamento padrão.
2. **Sizing Estrito de Parent Chunks:** O empacotador acumula blocos atômicos até o teto de `max_parent_tokens` (padrão: 1.000 a 1.200 tokens). Quando o próximo bloco atômico ultrapassar o limite, o chunk atual é selado e um novo chunk é aberto.
3. **Divisão Recursiva de Emergência (Fallback de Exceção):** Se um único bloco atômico (ex: um parágrafo contínuo de 2.500 tokens sem quebra de linha) exceder `max_parent_tokens`, o chunker aplica divisão por pontuação final (`(?<=[.!?])\s+`). Se uma frase única for maior que o limite, divide em limites de palavras (`\s+`). Tabelas e códigos que excedam o limite são divididos por linhas (`\n`).
4. **Child Chunks com Overlap Contextual:** Para cada `ParentChunk`, são gerados `ChildChunk`s (150 a 250 tokens) respeitando pontuação e preservando 30 tokens de overlap semântico para vetorização no Gemini Embedding 2.
5. **Breadcrumb / Header Path Best-Effort:** Se cabeçalhos (`#`, `##`) estiverem presentes no fluxo do texto, eles compõem o `header_path` contextual. Caso contrário, o chunker rotula de forma limpa como `[Doc: {doc_name}] > Part {index}`.

---

## Tech Stack
- **Linguagem & Runtime:** Python 3.12+
- **Tipagem Estrita:** Mypy (`strict = true`) sem uso implícito de `Any`
- **Validação & VOs:** Dataclasses imutáveis (`frozen=True`) / Pydantic v2
- **Qualidade & Testes:** Ruff (linter/formatter) e Pytest com `pytest-asyncio`

---

## Commands
```bash
# Executar suíte de testes unitários do chunker
uv run pytest tests/unit/test_structure_tolerant_markdown_chunker.py -v

# Validação de tipos estritos
uv run mypy src/modules/knowledge/infrastructure/chunking/

# Linter e formatação
uv run ruff check src/modules/knowledge/infrastructure/chunking/
uv run ruff format --check src/modules/knowledge/infrastructure/chunking/
```

---

## Project Structure (Single Class per File)
```
src/modules/knowledge/
├── domain/
│   ├── interfaces/
│   │   └── i_markdown_chunker.py                  # Protocol com método assíncrono chunk()
│   └── value_objects/
│       ├── parent_chunk.py                        # VO de Parent Chunk (id, header_path, content, token_count)
│       ├── child_chunk.py                         # VO de Child Chunk (id, parent_chunk_id, content, embedding)
│       ├── atomic_block.py                        # VO interno representando bloco atômico identificado
│       └── document_chunk_collection.py           # Agrupador com lista de parents e children
└── infrastructure/
    └── chunking/
        ├── atomic_block_lexer.py                  # Lexer sintático que extrai blocos indivisíveis
        ├── structure_tolerant_markdown_chunker.py # Implementação IMarkdownChunker com empacotamento guloso
        └── __init__.py                            # Facade exportadora pública
```

---

## Code Style & Architecture Conventions

### 1. Modelagem do Bloco Atômico
```python
# src/modules/knowledge/domain/value_objects/atomic_block.py
from dataclasses import dataclass
from enum import StrEnum


class AtomicBlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    TABLE = "table"
    LIST = "list"
    BLOCKQUOTE = "blockquote"
    THEMATIC_BREAK = "thematic_break"


@dataclass(frozen=True)
class AtomicBlock:
    content: str
    block_type: AtomicBlockType
    estimated_tokens: int
    header_level: int | None = None
    header_title: str | None = None
```

### 2. Algoritmo de Empacotamento Guloso
```python
# Trecho de empacotamento no structure_tolerant_markdown_chunker.py
for block in atomic_blocks:
    if current_tokens + block.estimated_tokens <= self._max_parent_tokens:
        current_blocks.append(block)
        current_tokens += block.estimated_tokens
    else:
        # Fechamento limpo do ParentChunk sem quebra no meio de blocos atômicos
        if current_blocks:
            parent_chunks.append(self._build_parent_chunk(current_blocks, parent_index))
            parent_index += 1
        current_blocks = [block]
        current_tokens = block.estimated_tokens
```

---

## Testing Strategy
- **`tests/unit/test_structure_tolerant_markdown_chunker.py`**:
  - Teste 1: Documento com tabelas Markdown extensas (garantir que nenhuma linha ou cabeçalho de tabela é cortado).
  - Teste 2: Documento com blocos de código cercados (garantir integridade de cercas ```` ``` ````).
  - Teste 3: Documento sem nenhum cabeçalho `#` (garantir divisão limpa em `Part 1`, `Part 2`...).
  - Teste 4: Documento legislativo (CF/88 simulada) com artigos e parágrafos curtos.
  - Teste 5: Caso limite com parágrafo gigante único (> 2.000 tokens) ativando o fallback por pontuação.
  - Teste 6: Validação do overlap e contagem de tokens dos Child Chunks gerados.

---

## Boundaries
- **Always:**
  - Garantir 1 classe por arquivo isolado.
  - Respeitar estritamente a tipagem `mypy --strict`.
  - Fechar chunks estritamente em fronteiras de blocos atômicos sempre que o bloco couber no orçamento de tokens.
- **Ask first:**
  - Alteração nos limites padrão de tokens (`max_parent_tokens=1200`, `child_chunk_tokens=200`).
- **Never:**
  - Quebrar o meio de uma linha de tabela ou o meio de um bloco cercado de código.
  - Deixar de gerar Child Chunks vinculados a seus respectivos `parent_chunk_id`.

---

## Success Criteria
- [ ] O `StructureTolerantMarkdownChunker` divide documentos de qualquer tipo sem corromper sintaxe Markdown.
- [ ] 100% dos Parent Chunks respeitam o teto de 1.200 tokens.
- [ ] Child Chunks geram slices de 150 a 250 tokens com 30 tokens de overlap semântico.
- [ ] Suíte de testes unitários com cobertura >= 95%.
- [ ] Aprovação total no gate `make pre-commit`.
