# Task List: Universal Structure-Tolerant Markdown Parent-Child Chunker

## Phase 1: Domain Value Objects & Models

### Task 1: Value Object `AtomicBlock` e Enum `AtomicBlockType`
**Description:** Criar o enum `AtomicBlockType` e o dataclass imutável `AtomicBlock` no domínio do módulo Knowledge para representar sintaticamente cada elemento atômico extraído pelo lexer.

**Acceptance criteria:**
- [x] `AtomicBlockType` implementado como `StrEnum` com membros: `HEADING`, `PARAGRAPH`, `CODE_BLOCK`, `TABLE`, `LIST`, `BLOCKQUOTE`, `THEMATIC_BREAK`.
- [x] `AtomicBlock` implementado como dataclass `frozen=True` contendo `content`, `block_type`, `estimated_tokens`, `header_level`, `header_title`.
- [x] 1 Classe por arquivo isolado e exportado em `src/modules/knowledge/domain/value_objects/__init__.py`.

**Verification:**
- [x] Teste unitário de instanciação e imutabilidade dos value objects.
- [x] `uv run mypy src/modules/knowledge/domain/value_objects/`

**Dependencies:** None
**Files touched:**
- `src/modules/knowledge/domain/value_objects/atomic_block_type.py`
- `src/modules/knowledge/domain/value_objects/atomic_block.py`
- `src/modules/knowledge/domain/value_objects/__init__.py`
- `tests/unit/test_chunk_value_objects.py`
**Estimated scope:** Small (3-4 files)

---

## Checkpoint: Domain Foundation
- [x] Value objects tipados com `strict = true` e testados unitariamente.

---

## Phase 2: Lexer Sintático de Blocos Atômicos

### Task 2: Implementar `AtomicBlockLexer`
**Description:** Implementar a máquina de estados `AtomicBlockLexer` que processa uma string de Markdown linha a linha e extrai a sequência de blocos atômicos sem cortar tabelas, blocos de código ou parágrafos.

**Acceptance criteria:**
- [x] Detecta blocos cercados de código (```` ```...``` ````) e mantém todas as linhas contidas em um único bloco `CODE_BLOCK`.
- [x] Detecta tabelas Markdown (`|...|`) completas como uma única unidade `TABLE`.
- [x] Detecta cabeçalhos (`#` a `######`) extraindo o nível (1 a 6) e o título limpo como `HEADING`.
- [x] Detecta parágrafos separados por quebras duplas `\n\n` como `PARAGRAPH`.
- [x] Calcula `estimated_tokens` para cada bloco baseado em `chars_per_token` configurável (padrão: 4).

**Verification:**
- [x] `uv run pytest tests/unit/test_atomic_block_lexer.py -v`
- [x] `uv run mypy src/modules/knowledge/infrastructure/chunking/atomic_block_lexer.py`

**Dependencies:** Task 1
**Files touched:**
- `src/modules/knowledge/infrastructure/chunking/atomic_block_lexer.py`
- `src/modules/knowledge/infrastructure/chunking/__init__.py`
**Estimated scope:** Small (2 files)

### Task 3: Testes Unitários Abrangentes do `AtomicBlockLexer`
**Description:** Criar suíte de testes unitários para o `AtomicBlockLexer` cobrindo cenários com código Python/SQL, tabelas complexas, texto sem formatação, cabeçalhos aninhados e quebras de linha variadas.

**Acceptance criteria:**
- [x] Teste de código multilinha cercado por crases triplas.
- [x] Teste de tabela Markdown com cabeçalho e múltiplas linhas.
- [x] Teste de cabeçalhos de níveis 1 a 6.
- [x] Teste de parágrafos normais e texto vazio.

**Verification:**
- [x] `uv run pytest tests/unit/test_atomic_block_lexer.py -v` com 100% de cobertura no lexer.

**Dependencies:** Task 2
**Files touched:**
- `tests/unit/test_atomic_block_lexer.py`
**Estimated scope:** Small (1 file)

---

## Checkpoint: Lexer Capabilities
- [x] `AtomicBlockLexer` divide qualquer texto em blocos atômicos com 100% de precisão nos testes.

---

## Phase 3: Empacotador Guloso & Structure-Tolerant Chunker

### Task 4: Implementar `StructureTolerantMarkdownChunker`
**Description:** Implementar a classe `StructureTolerantMarkdownChunker` conforme o contrato `IMarkdownChunker`, consumindo os blocos atômicos do lexer, aplicando empacotamento guloso para gerar `ParentChunk`s e gerando `ChildChunk`s com overlap contextual de 30 tokens.

**Acceptance criteria:**
- [x] Empacota blocos atômicos em `ParentChunk`s respeitando o teto de `max_parent_tokens` (padrão: 1.200).
- [x] Constrói `header_path` contextual atualizado dinamicamente por blocos `HEADING` ou fallback para `[Doc: {name}] > Part {N}`.
- [x] Aplica divisão por sentenças `(?<=[.!?])\s+` apenas quando um único bloco atômico exceder `max_parent_tokens`.
- [x] Gera `ChildChunk`s de 150 a 250 tokens com 30 tokens de overlap dentro de cada `ParentChunk`.
- [x] Retorna um `DocumentChunkCollection` completo e imutável.

**Verification:**
- [x] `uv run pytest tests/unit/test_structure_tolerant_markdown_chunker.py -v`
- [x] `uv run mypy src/modules/knowledge/infrastructure/chunking/structure_tolerant_markdown_chunker.py`

**Dependencies:** Task 2, Task 3
**Files touched:**
- `src/modules/knowledge/infrastructure/chunking/structure_tolerant_markdown_chunker.py`
- `src/modules/knowledge/infrastructure/chunking/__init__.py`
**Estimated scope:** Small (2 files)

### Task 5: Testes Unitários de Cenários e Edge Cases do Chunker
**Description:** Escrever suíte de testes cobrindo documentos reais de diferentes domínios (Constituição/leis, relatórios com tabelas financeiras, manuais técnicos de TI com código, texto puro sem cabeçalhos e parágrafos anômalos gigantes).

**Acceptance criteria:**
- [x] Teste garantindo que tabelas e blocos de código não são quebrados em pedaços arbitrários.
- [x] Teste de documento sem nenhum cabeçalho `#` gerando partes numeradas e ordenadas.
- [x] Teste de documento legislativo com artigos e parágrafos curtos.
- [x] Teste com parágrafo gigante único ativando o split por pontuação.
- [x] Teste de validação de `ChildChunk` (índices, `parent_chunk_id`, overlap semântico).

**Verification:**
- [x] `uv run pytest tests/unit/test_structure_tolerant_markdown_chunker.py -v`

**Dependencies:** Task 4
**Files touched:**
- `tests/unit/test_structure_tolerant_markdown_chunker.py`
**Estimated scope:** Small (1 file)

---

## Checkpoint: Chunker Validation
- [x] `StructureTolerantMarkdownChunker` cobre todos os requisitos funcionais e de edge cases com testes passando.

---

## Phase 4: Integração, Facades & Quality Gates

### Task 6: Atualizar Exports, Facades e Compatibilidade com a Saga
**Description:** Atualizar a facade `src/modules/knowledge/infrastructure/chunking/__init__.py`, injetar o `StructureTolerantMarkdownChunker` no `DocumentIngestionSagaCoordinator` e container IoC, mantendo alias com `MarkdownParentChildChunker` para retrocompatibilidade.

**Acceptance criteria:**
- [x] `DocumentIngestionSagaCoordinator` utiliza o `StructureTolerantMarkdownChunker` por padrão.
- [x] Container IoC (`src/api_gateway/container.py`) inicializa o chunker atualizado.
- [x] Todos os testes de integração existentes (`test_knowledge_module.py`, `test_markdown_parent_child_chunker.py`) continuam 100% verdes.

**Verification:**
- [x] `uv run pytest tests/ -v`

**Dependencies:** Task 4, Task 5
**Files touched:**
- `src/modules/knowledge/infrastructure/chunking/__init__.py`
- `src/modules/knowledge/application/sagas/document_ingestion_saga_coordinator.py`
- `src/api_gateway/container.py`
**Estimated scope:** Small (3 files)

### Task 7: Execução Completa dos Gates de Qualidade (`make pre-commit`)
**Description:** Executar a suíte completa de verificação de qualidade do projeto: Ruff linter, Ruff formatador, checagem estrita de tipos no Mypy e todos os testes automatizados com medição de cobertura.

**Acceptance criteria:**
- [x] `uv run ruff check .` com zero erros e zero warnings.
- [x] `uv run ruff format --check .` 100% formatado.
- [x] `uv run mypy src tests` com `Success: no issues found`.
- [x] `uv run pytest --cov=src` com 100% dos testes passando.
- [x] Execução com sucesso do comando `make pre-commit`.

**Verification:**
- [x] `make pre-commit`

**Dependencies:** Task 6
**Files touched:**
- Todos os arquivos alterados
**Estimated scope:** Small

---

## Checkpoint: Final
- [x] Todo o particionador universal structure-tolerant integrado, testado e aprovado no gate oficial.
