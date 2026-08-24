# SPEC: Markdown Continuity Normalizer (Marco 1.19)

## 1. Objetivo

O parser VLM (`ParallelVlmDocumentParser`) transcreve PDFs página a página em paralelo e concatena os resultados com marcadores `<!-- PAGE N -->`. Embora a hierarquia de cabeçalhos seja injetada via `hierarchy_hint` (proveniente do `SyntheticDocumentToc`), o `system_prompt` atual em produção é mais pobre que o POC (`poc_sliding_window_ocr.py`): **três regras de continuidade** presentes no POC nunca migraram para o parser de produção.

**Resultado atual:** Markdown com artefatos de paginação que prejudicam o chunking e o retrieval:
- `<!-- PAGE N -->` como conteúdo nos chunks (sem valor semântico, poluem o índice)
- Headers de seção duplicados entre páginas (uma mesma seção aparece como N seções distintas no chunker)
- Tabelas cortadas entre páginas sem repetição do header de colunas (rows ficam sem contexto)
- Parágrafos com quebra de linha forçada na fronteira de páginas

**Objetivo:** Produzir um Markdown contínuo e semanticamente limpo como saída de `parse_to_markdown`, sem alterar a arquitetura de checkpoints, paralelismo ou o contrato de `IDocumentParser`.

**Quem se beneficia:** Todo pipeline downstream — `StructureTolerantMarkdownChunker`, `AtomicBlockLexer`, extrator de grafos e retrieval via RAG.

**Sucesso:** Um documento PDF com uma seção que ocupa 3 páginas gera **um único heading** para essa seção no Markdown final, sem `<!-- PAGE N -->` visíveis, com tabelas inter-página tendo seus headers repetidos, e whitespace normalizado.

---

## 2. Escopo e Não-Escopo

### ✅ Incluído

1. **Prompt Enrichment** — Migrar as 3 regras de continuidade do POC (`poc_sliding_window_ocr.py` L41-L60) para o `system_prompt` de `_transcribe_single_page` em `ParallelVlmDocumentParser`:
   - Regra de continuidade de hierarquia: não criar títulos artificiais se a página continua uma seção existente
   - Regra de continuidade de texto: não forçar quebra de parágrafo se a primeira linha é continuação da página anterior
   - Regra de tabelas inter-página: repetir o header de colunas quando a tabela começou na página anterior

2. **Post-Processor Determinístico** — Novo método `_normalize_markdown(raw: str) -> str` (privado, chamado na concatenação final em `parse_to_markdown`):
   - Remove marcadores `<!-- PAGE N -->` e `<!-- [Erro no OCR da Página N: ...] -->`
   - Deduplica headers adjacentes semanticamente idênticos (normalização de whitespace + case antes de comparar)
   - Colapsa sequências de `\n\n\n+` em `\n\n` (máximo 2 newlines consecutivos)
   - Normalização aplicada nos dois pontos de concatenação: fast-path de cache (L226) e path padrão (L296-298)

3. **Atualização de Testes** — Os testes que hoje assertam `<!-- PAGE 1 -->` devem ser atualizados para assertar a **ausência** dos markers e a **presença** do conteúdo sem markers.

4. **Atualização da SPEC-synthetic-toc-and-parallel-vlm-ocr.md** — Refletir o novo behavior na seção 2 (diagrama de sequência) e na seção 6 (critérios de sucesso).

5. **Atualização do CAPABILITY-MAP.md** — Registrar o Marco 1.19.

### ❌ Não-Escopo

- **Sliding window sequential** — Não mudamos o modelo de paralelismo concorrente.
- **Merge semântico de tabelas via LLM** — A detecção e merge de tabelas partidas entre páginas é feita **no prompt** (instrução ao VLM), não por pós-processamento programático avançado.
- **Novo adapter ou interface** — Tudo permanece dentro de `ParallelVlmDocumentParser`; sem novos arquivos de adapter.
- **Mudanças no chunker** — `StructureTolerantMarkdownChunker` e `AtomicBlockLexer` permanecem intocados.
- **Rastreabilidade de página via conteúdo inline** — Page metadata será tratada em spec futura se houver demanda. Por ora, Markdown limpo é a saída.

---

## 3. Componentes Afetados

| Arquivo | Mudança |
|---|---|
| `src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py` | Enriquecer `system_prompt` em `_transcribe_single_page` + adicionar `_normalize_markdown()` + aplicar nos dois pontos de concatenação (L226 e L296-298) |
| `tests/unit/test_parallel_vlm_document_parser.py` | Atualizar assertions que validavam presença de `<!-- PAGE N -->` para validar **ausência** + adicionar 7 novos casos unitários do normalizer |
| `SPEC-synthetic-toc-and-parallel-vlm-ocr.md` | Atualizar diagrama de sequência (passo de normalização pós-concat) e critérios de sucesso |
| `CAPABILITY-MAP.md` | Adicionar Marco 1.19 |

---

## 4. Contrato de Comportamento (Acceptance Criteria Precisos)

### 4.1 Prompt Enrichment

O `system_prompt` de `_transcribe_single_page` DEVE conter, além das regras existentes:

```
5. Continuidade de Hierarquia:
   - Se o topo da página exibir um título que já está na hierarquia ativa,
     NÃO o repita — a página é continuação de uma seção já aberta.
   - Só emita um cabeçalho se ele for genuinamente novo em relação à hierarquia ativa.
6. Continuidade de Texto:
   - Se a primeira linha da página for continuação de um parágrafo anterior (sem título novo),
     continue o texto diretamente sem inserir quebra de parágrafo forçada.
7. Tabelas Inter-Página:
   - Se a página atual exibir linhas de uma tabela que começou em página anterior,
     repita o cabeçalho de colunas (linha `| Col1 | Col2 |` e linha `|---|---|`)
     antes das linhas de dados, para manter a tabela GFM auto-contida.
```

### 4.2 Post-Processor `_normalize_markdown`

Dado `raw` como string de entrada (saída da concatenação de páginas):

| Caso de entrada | Resultado esperado |
|---|---|
| `"<!-- PAGE 1 -->\nConteúdo"` | `"Conteúdo"` |
| `"<!-- [Erro no OCR da Página 3: timeout] -->"` | `""` (string vazia) |
| `"## Intro\n\n<!-- PAGE 2 -->\n\n## Intro\n\nTexto"` | `"## Intro\n\nTexto"` (header deduplicado) |
| `"## Intro\n\n<!-- PAGE 2 -->\n\n## Intro Revisitada\n\nTexto"` | `"## Intro\n\n## Intro Revisitada\n\nTexto"` (headers distintos → preservados) |
| `"Fim\n\n\n\n\nInício"` | `"Fim\n\nInício"` (max 2 newlines) |
| `"## A\n\n## B"` | `"## A\n\n## B"` (headers distintos → intactos) |

**Regra de deduplicação de headers:** Dois headers `H_prev` e `H_curr` são considerados duplicados se e somente se `normalize(H_prev) == normalize(H_curr)`, onde `normalize(s)` remove os `#` prefixados, faz strip e converte para lowercase. Apenas `H_curr` é removido (mantém o primeiro). A remoção ocorre apenas entre headers **adjacentes** — sem conteúdo de parágrafo entre eles, apenas whitespace ou page markers já removidos.

### 4.3 Integração

- `_normalize_markdown` é chamado **após** a concatenação em `"\n\n".join(output_blocks)` (substituindo o `return` atual na linha 298).
- `_normalize_markdown` também é chamado no fast-path de cache (linha 226), antes do `return`.
- A saída final de `parse_to_markdown` NUNCA contém a substring `<!-- PAGE`.
- A saída final NUNCA contém a substring `<!-- [Erro`.
- A saída final NUNCA tem mais que dois `\n` consecutivos.
- A saída final preserva integralmente o conteúdo semântico (tabelas, listas, blockquotes, code blocks).

---

## 5. Tech Stack e Comandos

```
Linguagem: Python 3.12+
Tipagem:   mypy strict (zero Any implícito, zero type: ignore)
Linter:    ruff check . && ruff format --check .
Testes:    pytest tests/unit/test_parallel_vlm_document_parser.py -v
Gate:      make pre-commit
```

---

## 6. Estrutura de Arquivos

```
src/modules/knowledge/infrastructure/adapters/
└── parallel_vlm_document_parser.py     ← único arquivo modificado em src/

tests/unit/
└── test_parallel_vlm_document_parser.py  ← testes atualizados + 7 novos

SPEC-synthetic-toc-and-parallel-vlm-ocr.md   ← atualizar seções 2 e 6
CAPABILITY-MAP.md                             ← adicionar Marco 1.19
SPEC-markdown-continuity-normalizer.md        ← este documento (novo)
```

---

## 7. Estilo de Código

Constantes de regex compiladas no nível de módulo (fora da classe):

```python
import re

_PAGE_MARKER_RE: re.Pattern[str] = re.compile(r"<!--\s*PAGE\s*\d+\s*-->")
_ERROR_MARKER_RE: re.Pattern[str] = re.compile(r"<!--\s*\[Erro no OCR.*?\]\s*-->", re.DOTALL)
_EXCESS_NEWLINES_RE: re.Pattern[str] = re.compile(r"\n{3,}")
_HEADING_RE: re.Pattern[str] = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
```

Método privado com docstring em português:

```python
def _normalize_markdown(self, raw: str) -> str:
    """Remove artefatos de paginação e normaliza whitespace do Markdown concatenado."""
    text = _PAGE_MARKER_RE.sub("", raw)
    text = _ERROR_MARKER_RE.sub("", text)
    text = _EXCESS_NEWLINES_RE.sub("\n\n", text)
    text = self._dedup_adjacent_headers(text)
    return text.strip()


def _dedup_adjacent_headers(self, text: str) -> str:
    """Remove headers duplicados adjacentes, mantendo o primeiro."""
    ...
```

Convenções mantidas do projeto:
- Métodos privados com prefixo `_`
- Tipagem explícita em todos os métodos e retornos
- Zero `# type: ignore`
- Zero `Any` implícito

---

## 8. Estratégia de Testes

**Framework:** `pytest` + `pytest-asyncio`  
**Localização:** `tests/unit/test_parallel_vlm_document_parser.py`

### 8.1 Casos Unitários Novos (normalizer isolado)

```
test_normalize_removes_page_markers
  → "<!-- PAGE 1 -->\nConteúdo" ⟹ "Conteúdo"

test_normalize_removes_error_markers
  → "<!-- [Erro no OCR da Página 3: timeout] -->" ⟹ ""

test_normalize_deduplicates_adjacent_identical_headers
  → "## Intro\n\n<!-- PAGE 2 -->\n\n## Intro\n\nTexto" ⟹ "## Intro\n\nTexto"

test_normalize_preserves_distinct_adjacent_headers
  → "## Intro\n\n## Métodos\n\nTexto" ⟹ preservado integralmente

test_normalize_dedup_is_case_and_whitespace_insensitive
  → "## Introdução\n\n##  introdução \n\nTexto" ⟹ deduplicado

test_normalize_collapses_excess_newlines
  → "Fim\n\n\n\n\nInício" ⟹ "Fim\n\nInício"

test_normalize_preserves_tables_code_blocks_and_lists
  → Markdown com tabela GFM, fenced code block e lista — saída idêntica (sem markers)
```

### 8.2 Casos Existentes Atualizados

```
test_parallel_vlm_ocr_success
  ANTES: assert "<!-- PAGE 1 -->" in markdown
  DEPOIS: assert "<!-- PAGE 1 -->" not in markdown
          assert "## 1. Introduction" in markdown  # conteúdo preservado

test_parallel_vlm_parser_fast_path_when_all_pages_cached
  ADICIONAR: assert "<!-- PAGE 1 -->" not in markdown
             assert "Cached Page 1 Content" in markdown
```

**Cobertura mínima:** Todos os novos 7 casos passando + todos os existentes adaptados passando.

---

## 9. Boundaries

- **Always:** Executar `make pre-commit` antes de qualquer commit; tipagem mypy strict sem Any implícito; single class per file (nenhuma nova classe neste Marco).
- **Ask first:** Qualquer mudança na assinatura de `IDocumentParser`; qualquer novo arquivo de adapter; mudança no sistema de checkpoints de página.
- **Never:** Alterar `AtomicBlockLexer`, `StructureTolerantMarkdownChunker` ou `MarkdownParentChildChunker`; introduzir segundo passe de LLM para normalização; remover o paralelismo concorrente de OCR; commitar sem `make pre-commit` passando.

---

## 10. Critérios de Sucesso

- [ ] `make pre-commit` passa com zero erros (mypy strict, ruff, pytest 100%)
- [ ] `parse_to_markdown` nunca retorna string contendo `<!-- PAGE`
- [ ] `parse_to_markdown` nunca retorna string contendo `<!-- [Erro`
- [ ] Nenhum `\n\n\n` (3+ newlines consecutivos) na saída
- [ ] Header duplicado entre páginas adjacentes resulta em 1 único heading (validado em teste unitário com mock)
- [ ] Fast-path de cache (100% páginas cached) também normaliza corretamente
- [ ] O `system_prompt` em `_transcribe_single_page` contém as 3 novas regras de continuidade (validado via assert de string no teste)
- [ ] `SPEC-synthetic-toc-and-parallel-vlm-ocr.md` reflete o novo passo de normalização pós-concat
- [ ] `CAPABILITY-MAP.md` registra Marco 1.19 como Em Andamento (v0.3.8)

---

## 11. Open Questions

Nenhuma questão bloqueante. Decisões já tomadas nesta spec:
- Page metadata (rastreabilidade de origem por trecho) → fora de escopo por ora.
- Sliding window sequential → não adotado (quebra paralelismo e checkpoints).
- Merge programático de tabelas partidas → delegado ao prompt VLM.
