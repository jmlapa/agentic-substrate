# Task List: Markdown Continuity Normalizer (Marco 1.19)

> **Executor:** Use a skill `incremental-implementation` em cada task.
> **Regra de ouro:** Implement → Test → Verify (passing) → Commit. Nunca commitar com testes falhando.
> **Testes anti-vício:** Os testes do normalizer usam strings literais fixas como entrada e assertam strings literais como saída. Não usar mocks para testar funções puras.

---

## Phase 1: Fundação (sem mudança de comportamento externo)

### Task 1: Adicionar constantes de regex no nível de módulo

**Description:** Declara as 4 constantes `re.Pattern[str]` compiladas fora da classe `ParallelVlmDocumentParser`, logo após os imports existentes. Nenhuma lógica é alterada nesta task — apenas declarações de constantes. O sistema continua funcionando exatamente igual.

**Acceptance criteria:**
- [ ] 4 constantes declaradas com tipagem explícita `re.Pattern[str]`:
  - `_PAGE_MARKER_RE = re.compile(r"<!--\s*PAGE\s*\d+\s*-->")`
  - `_ERROR_MARKER_RE = re.compile(r"<!--\s*\[Erro no OCR.*?\]\s*-->", re.DOTALL)`
  - `_EXCESS_NEWLINES_RE = re.compile(r"\n{3,}")`
  - `_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)`
- [ ] Nenhuma lógica existente modificada
- [ ] `ruff check` e `mypy src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py` limpos

**Verification:**
```bash
uv run ruff check src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py
uv run mypy src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py
uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v
```
Todos os testes existentes devem passar sem alteração.

**Dependencies:** None

**Files touched:**
- `src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py` (somente adição de constantes)

**Estimated scope:** XS (1 arquivo, ~5 linhas)

**Commit:** `feat(knowledge): add module-level regex constants for markdown normalizer`

---

### Task 2: Implementar `_dedup_adjacent_headers()` + testes unitários

**Description:** Adiciona o método privado `_dedup_adjacent_headers(self, text: str) -> str` à classe `ParallelVlmDocumentParser`. O método varre o texto linha a linha, identificando headers `# ... ######` adjacentes (separados apenas por whitespace) e removendo duplicatas — mantendo o primeiro. A normalização de comparação: strip dos `#` + strip + lowercase. Adiciona 3 testes unitários diretos ao método (chamando-o via instância sem mocks).

**Acceptance criteria:**
- [ ] Método `_dedup_adjacent_headers` implementado com tipagem `str -> str`
- [ ] Dois headers adjacentes idênticos (case-insensitive, whitespace-insensitive nos `#`) → apenas o primeiro sobrevive
- [ ] Dois headers adjacentes **distintos** → ambos preservados
- [ ] Headers separados por parágrafo de conteúdo → ambos preservados (não são adjacentes)
- [ ] 3 testes unitários passando: `test_dedup_removes_identical_adjacent`, `test_dedup_preserves_distinct_adjacent`, `test_dedup_ignores_non_adjacent`

**Verification:**
```bash
uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v -k "dedup"
uv run mypy src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py
```

**Dependencies:** Task 1

**Files touched:**
- `src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py` (método privado adicionado)
- `tests/unit/test_parallel_vlm_document_parser.py` (3 novos testes)

**Estimated scope:** S (2 arquivos, ~40 linhas)

**Commit:** `feat(knowledge): implement _dedup_adjacent_headers with unit tests`

> ⚠️ Anti-vício: Os testes chamam `parser._dedup_adjacent_headers(input_str)` e assertam `== expected_str` com strings literais. Não usar `MagicMock` ou `patch`.

---

### Task 3: Implementar `_normalize_markdown()` + 7 testes unitários novos

**Description:** Adiciona o método `_normalize_markdown(self, raw: str) -> str` que orquestra: (1) remove page markers via `_PAGE_MARKER_RE`, (2) remove error markers via `_ERROR_MARKER_RE`, (3) colapsa excess newlines via `_EXCESS_NEWLINES_RE`, (4) chama `_dedup_adjacent_headers`. Retorna `.strip()`. Nenhum ponto de saída do parser é alterado ainda — o método existe mas não é chamado em produção. Adiciona 7 novos testes unitários ao arquivo de testes.

**Acceptance criteria:**
- [ ] Método `_normalize_markdown` implementado com tipagem `str -> str`
- [ ] 7 testes unitários passando (todos chamando `parser._normalize_markdown(input)` diretamente):
  1. `test_normalize_removes_page_markers` — `"<!-- PAGE 1 -->\nConteúdo"` → `"Conteúdo"`
  2. `test_normalize_removes_error_markers` — `"<!-- [Erro no OCR da Página 3: timeout] -->"` → `""`
  3. `test_normalize_deduplicates_adjacent_identical_headers` — `"## Intro\n\n<!-- PAGE 2 -->\n\n## Intro\n\nTexto"` → `"## Intro\n\nTexto"`
  4. `test_normalize_preserves_distinct_adjacent_headers` — `"## Intro\n\n## Métodos\n\nTexto"` → intacto
  5. `test_normalize_dedup_is_case_and_whitespace_insensitive` — `"## Introdução\n\n##  introdução \n\nTexto"` → deduplicado
  6. `test_normalize_collapses_excess_newlines` — `"Fim\n\n\n\n\nInício"` → `"Fim\n\nInício"`
  7. `test_normalize_preserves_tables_code_blocks_and_lists` — Markdown com tabela GFM e fenced code block → mesma saída (sem markers, conteúdo intacto)

**Verification:**
```bash
uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v -k "normalize"
uv run mypy src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py
```

**Dependencies:** Task 2

**Files touched:**
- `src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py` (método adicionado)
- `tests/unit/test_parallel_vlm_document_parser.py` (7 novos testes)

**Estimated scope:** S (2 arquivos, ~60 linhas)

**Commit:** `feat(knowledge): implement _normalize_markdown with 7 unit tests`

> ⚠️ Anti-vício: Cada teste usa uma string de entrada **fixa e literal** e asserta uma string de saída **fixa e literal**. Nenhum mock. Nenhum `assert True`. Nenhum `assert len(result) > 0` sem verificar o conteúdo.

---

## Checkpoint 1: Fundação
- [ ] `uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v` — todos passando (todos os existentes + 10 novos)
- [ ] `uv run mypy src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py` — zero erros

---

## Phase 2: Integração (mudança de comportamento externo)

### Task 4: Aplicar `_normalize_markdown` nos 2 pontos de saída + atualizar assertions existentes

**Description:** Esta task muda o comportamento externo de `parse_to_markdown`. São duas alterações acopladas que DEVEM ir no mesmo commit (não é possível fazer uma sem a outra sem quebrar os testes):

**Alteração A — fast-path de cache (L226):**
```python
# ANTES:
cached_blocks.append(f"<!-- PAGE {p} -->\n{p_content or ''}")
return "\n\n".join(cached_blocks)

# DEPOIS:
cached_blocks.append(p_content or "")
return self._normalize_markdown("\n\n".join(cached_blocks))
```

**Alteração B — path normal (L293-298):**
```python
# ANTES:
output_blocks.append(f"<!-- PAGE {page_num} -->\n{page_results.get(page_num, '')}")
return "\n\n".join(output_blocks)

# DEPOIS:
output_blocks.append(page_results.get(page_num, ""))
return self._normalize_markdown("\n\n".join(output_blocks))
```

**Alteração C — testes existentes:**
- Em `test_parallel_vlm_ocr_success`: trocar `assert "<!-- PAGE 1 -->" in markdown` por `assert "<!-- PAGE 1 -->" not in markdown` e adicionar `assert "## 1. Introduction" in markdown`.
- Em `test_parallel_vlm_parser_fast_path_when_all_pages_cached`: adicionar `assert "<!-- PAGE 1 -->" not in markdown`.

**Acceptance criteria:**
- [ ] `parse_to_markdown` não contém `<!-- PAGE` na saída em nenhum cenário
- [ ] `parse_to_markdown` não contém `<!-- [Erro` na saída em nenhum cenário
- [ ] Conteúdo semântico (headers, tabelas, parágrafos) preservado na saída
- [ ] Todos os testes existentes passam com as assertions atualizadas
- [ ] Todos os 10 testes novos (Tasks 2 e 3) continuam passando

**Verification:**
```bash
uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v
uv run mypy src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py
uv run ruff check src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py
```

**Dependencies:** Task 3

**Files touched:**
- `src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py` (L226 e L293-298)
- `tests/unit/test_parallel_vlm_document_parser.py` (2 assertions existentes atualizadas)

**Estimated scope:** S (2 arquivos, ~15 linhas alteradas)

**Commit:** `feat(knowledge): apply markdown normalizer to both output paths and update tests`

> ⚠️ Se os testes falharem após as alterações A+B+C, NÃO commitar. Diagnosticar a falha, corrigir e re-rodar antes de commitar.

---

## Checkpoint 2: Integração
- [ ] `uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v` — todos os testes passando
- [ ] Nenhuma saída de `parse_to_markdown` contém `<!-- PAGE`

---

## Phase 3: Prompt Enrichment

### Task 5: Enriquecer `system_prompt` com 3 regras de continuidade + teste de presença

**Description:** Modifica o `system_prompt` construído dentro de `_transcribe_single_page` para adicionar as 3 regras de continuidade que existem no POC (`poc_sliding_window_ocr.py`) mas não estão no parser de produção. Adiciona 1 teste que instancia o parser e verifica que o prompt contém as strings-chave das 3 regras.

As 3 regras a adicionar (após a regra 4 existente):
```
5. Continuidade de Hierarquia:
   - Se o topo desta página exibir um título que já está na hierarquia ativa acima,
     NÃO o repita — a página é continuação de uma seção já aberta.
   - Só emita um cabeçalho se ele for genuinamente novo em relação à hierarquia ativa.
6. Continuidade de Texto:
   - Se a primeira linha desta página for continuação de um parágrafo anterior (sem título novo),
     continue o texto diretamente sem inserir quebra de parágrafo forçada.
7. Tabelas Inter-Página:
   - Se esta página exibir linhas de uma tabela que começou em página anterior,
     repita o cabeçalho de colunas (| Col1 | Col2 | e |---|---|) antes das linhas de dados.
```

**Acceptance criteria:**
- [ ] O `system_prompt` em `_transcribe_single_page` contém as 3 novas regras
- [ ] 1 teste `test_transcribe_system_prompt_contains_continuity_rules` que:
  - Cria um `ParallelVlmDocumentParser` sem client (só para inspeção)
  - Extrai o prompt via uma chamada mock controlada (ou verifica o template como string)
  - Asserta que `"Continuidade de Hierarquia"` está no prompt
  - Asserta que `"Continuidade de Texto"` está no prompt
  - Asserta que `"Tabelas Inter-Página"` está no prompt
- [ ] Todos os testes existentes continuam passando

**Verification:**
```bash
uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v -k "prompt"
uv run pytest tests/unit/test_parallel_vlm_document_parser.py -v
uv run mypy src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py
```

**Dependencies:** Task 4

**Files touched:**
- `src/modules/knowledge/infrastructure/adapters/parallel_vlm_document_parser.py` (system_prompt em `_transcribe_single_page`)
- `tests/unit/test_parallel_vlm_document_parser.py` (1 novo teste)

**Estimated scope:** S (2 arquivos, ~20 linhas)

**Commit:** `feat(knowledge): enrich vlm system_prompt with 3 continuity rules and add prompt test`

> ⚠️ Estratégia para testar o prompt sem chamar a API: passar um `mock_client` que captura os argumentos do `create` call e assertar o `system` message. Não usar `assert True` nem `assert "regra" in "alguma string inventada"`.

---

## Phase 4: Docs & Gate Final

### Task 6: Atualizar docs (`SPEC-synthetic-toc-and-parallel-vlm-ocr.md` e `CAPABILITY-MAP.md`)

**Description:** Atualiza os dois documentos de spec para refletir o Marco 1.19 como concluído.

**Alteração em `SPEC-synthetic-toc-and-parallel-vlm-ocr.md`:**
- Na seção 2 (diagrama), adicionar o passo `Parser→Parser: _normalize_markdown(concatenated)` antes do `return`.
- Na seção 6 (critérios de sucesso), adicionar:
  - `[x] Markdown Contínuo: saída de parse_to_markdown nunca contém <!-- PAGE ou <!-- [Erro.`
  - `[x] Headers sem duplicatas: headers repetidos entre páginas adjacentes são deduplicados.`

**Alteração em `CAPABILITY-MAP.md`:**
- Adicionar linha na tabela de Especificações Técnicas: `SPEC-markdown-continuity-normalizer.md (Marco 1.19 - Markdown Continuity Normalizer) — Concluído (v0.3.8)`
- Adicionar step 10.5 na Ordem de Construção referenciando o Marco 1.19.

**Acceptance criteria:**
- [ ] `SPEC-synthetic-toc-and-parallel-vlm-ocr.md` seções 2 e 6 atualizadas
- [ ] `CAPABILITY-MAP.md` registra Marco 1.19 como Concluído (v0.3.8)

**Verification:**
```bash
# Apenas verificação visual — não há testes para docs
grep "1.19" /Users/insider/personal/agentic-substrate/CAPABILITY-MAP.md
grep "normalize" /Users/insider/personal/agentic-substrate/SPEC-synthetic-toc-and-parallel-vlm-ocr.md
```

**Dependencies:** Task 5

**Files touched:**
- `SPEC-synthetic-toc-and-parallel-vlm-ocr.md`
- `CAPABILITY-MAP.md`

**Estimated scope:** XS (2 arquivos de doc, ~10 linhas)

**Commit:** `docs: update spec and capability map for Marco 1.19`

---

### Task 7: Gate final — `make pre-commit`

**Description:** Executa o gate de qualidade completo do projeto para confirmar que o Marco 1.19 está pronto para merge.

**Acceptance criteria:**
- [ ] `ruff check .` — zero warnings/errors
- [ ] `ruff format --check .` — zero diffs
- [ ] `mypy src tests` — zero erros (strict mode)
- [ ] `pytest` — 100% dos testes passando (incluindo os novos 11 testes do Marco 1.19)

**Verification:**
```bash
make pre-commit
```

**Dependencies:** Task 6

**Files touched:** Nenhum (somente execução do gate)

**Estimated scope:** XS (gate only)

**Commit:** Nenhum commit nesta task — apenas verificação. Se falhar, voltar à task correspondente para corrigir antes do merge.

---

## Checkpoint Final: Marco 1.19 Completo

- [ ] `make pre-commit` — 100% verde (ruff + mypy + pytest)
- [ ] `parse_to_markdown` nunca emite `<!-- PAGE` ou `<!-- [Erro`
- [ ] 11 novos testes adicionados e passando
- [ ] Docs atualizados (SPEC + CAPABILITY-MAP)
- [ ] Branch `feature/markdown-continuity-normalizer` pronta para PR
