# Implementation Plan: Universal Structure-Tolerant Markdown Parent-Child Chunker

## Overview
Implementar o particionador hierárquico determinístico universal de Markdown (`StructureTolerantMarkdownChunker`), dividindo o documento em blocos atômicos indivisíveis (tabelas, blocos cercados de código, parágrafos, listas) e empacotando-os de forma gulosa em **Parent Chunks** de tamanho uniforme (800 a 1.200 tokens) e **Child Chunks** de alta resolução (150 a 250 tokens com 30 tokens de overlap). O particionador é 100% agnóstico a domínio (leis, TI, finanças, manuais) e resiliente a inconsistências de conversão de PDFs.

---

## Architecture Decisions

1. **Separação em Lexer Atômico e Empacotador Guloso (Single Responsibility)**:
   - `AtomicBlockLexer`: Responsável exclusivo por transformar a string bruta do Markdown em uma lista sequencial de `AtomicBlock`s estruturados com identificação de tipo (`HEADING`, `PARAGRAPH`, `CODE_BLOCK`, `TABLE`, `LIST`, `BLOCKQUOTE`, `THEMATIC_BREAK`) e estimativa de tokens.
   - `StructureTolerantMarkdownChunker`: Responsável exclusivo por acumular `AtomicBlock`s em `ParentChunk`s com sizing estrito, acionar divisão por sentenças apenas em blocos individuais anômalos e fatiar cada parent em `ChildChunk`s contextuais com overlap.

2. **Indivisibilidade Sintática Determinística**:
   - Nenhum bloco de código cercado (```` ```...``` ````) ou tabela Markdown (`|...|`) pode ser cortado no meio durante o empacotamento padrão.
   - Cortes normais entre chunks ocorrem estritamente na fronteira entre blocos atômicos (ex: entre parágrafos ou após uma tabela).

3. **Fallback de Emergência em Bloco Único Anômalo**:
   - Caso um único parágrafo sem quebras exceda `max_parent_tokens`, aplica corte por sentenças (`(?<=[.!?])\s+`).
   - Caso uma única tabela ou bloco de código exceda `max_parent_tokens`, aplica corte por linhas (`\n`).

4. **Rastreamento de Header Breadcrumb Best-Effort**:
   - Constrói o `header_path` dinamicamente conforme encontra blocos `HEADING` (`#`, `##`, etc.).
   - Se o documento não tiver nenhum cabeçalho (comum em PDFs convertidos), nomeia de forma limpa como `[Doc: {doc_name}] > Part {index}`.

5. **Conformidade Estrita com AGENTS.md**:
   - 1 Classe / 1 Interface / 1 Enum por arquivo.
   - Mypy `strict = true` em todos os módulos e testes.
   - Compatibilidade total com `IMarkdownChunker` e a Saga de Ingestão.

---

## Task List

### Phase 1: Domain Value Objects & Models
- [ ] **Task 1: Value Object `AtomicBlock` e Enum `AtomicBlockType`**
  - Modelar os blocos atômicos indivisíveis e seus tipos no domínio.

### Checkpoint: Domain Foundation
- [ ] VOs criados em arquivos isolados, tipados estritamente e exportados em facades.

### Phase 2: Lexer Sintático de Blocos Atômicos
- [ ] **Task 2: Implementar `AtomicBlockLexer`**
  - Criar lexer de máquina de estados para extração de tabelas, code blocks, cabeçalhos e parágrafos.
- [ ] **Task 3: Testes Unitários do `AtomicBlockLexer`**
  - Cobrir cenários de cercas de código, tabelas com colunas variadas, quebras duplas e cabeçalhos.

### Checkpoint: Lexer Capabilities
- [ ] `AtomicBlockLexer` isolado e validado com 100% de cobertura nos testes unitários.

### Phase 3: Empacotador Guloso & Structure-Tolerant Chunker
- [ ] **Task 4: Implementar `StructureTolerantMarkdownChunker`**
  - Implementar empacotamento guloso, divisão por sentenças em caso de overflow e geração de `ChildChunk`s com overlap.
- [ ] **Task 5: Testes Unitários de Cenários e Edge Cases do Chunker**
  - Testar integridade de tabelas, código, documentos sem cabeçalhos, textos legislativos e fallbacks.

### Checkpoint: Chunker Validation
- [ ] `StructureTolerantMarkdownChunker` implementado e aprovado em todos os testes unitários.

### Phase 4: Integração, Facades & Quality Gates
- [ ] **Task 6: Integração no Módulo Knowledge & Facades Públicas**
  - Atualizar exports em `src/modules/knowledge/infrastructure/chunking/__init__.py` e garantir retrocompatibilidade com `MarkdownParentChildChunker`.
- [ ] **Task 7: Execução Completa dos Gates de Qualidade (`make pre-commit`)**
  - Executar Pytest, Ruff linter, Ruff format e Mypy estrito.

### Checkpoint: Final
- [ ] 100% dos testes passando e zero erros no gate oficial pré-commit.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tabela ou bloco de código único gigante (> 1.200 tokens) estourar o limite | Médio | Fallback recursivo que particiona a tabela por linhas ou código por quebra de linha preservando cercas |
| Documentos sem cabeçalhos `#` gerarem títulos feios | Baixo | Geração automática de `header_path` estruturado `[Doc: {name}] > Part {N}` |
| Regressão na Saga de Ingestão existente | Alto | Manter assinatura idêntica no protocolo `IMarkdownChunker` e manter alias/facade compatível |

---

## Open Questions
- Nenhuma. O modelo de empacotamento guloso e blocos atômicos resolve a consistência para qualquer tipo de documento.
