# Task List: Marco 1.18 — Rich Markdown Renderer for RAG Playground

## Phase 1: Package Dependencies & Tailwind Setup
- [x] **Task 1: Install Markdown Dependencies & Configure Tailwind**
  - **Description:** Instalar `react-markdown`, `remark-gfm` e `@tailwindcss/typography` no frontend e registrar o plugin no `tailwind.config.js`.
  - **Acceptance criteria:**
    - [x] `react-markdown`, `remark-gfm` e `@tailwindcss/typography` presentes em `frontend/package.json`.
    - [x] `plugins: [typography]` adicionado a `frontend/tailwind.config.js`.
  - **Verify:** `cd frontend && npm list react-markdown remark-gfm @tailwindcss/typography`
  - **Files:** `frontend/package.json`, `frontend/tailwind.config.js`

---

## Phase 2: Core Components Implementation
- [x] **Task 2: Create CodeBlock Component**
  - **Description:** Implementar `frontend/src/components/ui/CodeBlock.tsx` com visualizador escuro de código, header com badge de linguagem e botão de cópia individual.
  - **Acceptance criteria:**
    - [x] Exibe a linguagem detectada (ex: `python`, `sql`, `json`, `text`).
    - [x] Botão de copiar copia o conteúdo do bloco para o clipboard e exibe check visual por 2s.
    - [x] Formatação mono com quebras de linha e scroll horizontal preservados.
  - **Verify:** `cd frontend && npm run type-check`
  - **Files:** `frontend/src/components/ui/CodeBlock.tsx`

- [x] **Task 3: Create Reusable MarkdownRenderer Component**
  - **Description:** Implementar `frontend/src/components/ui/MarkdownRenderer.tsx` integrando `ReactMarkdown`, `remarkGfm` e mapeando tags semânticas para componentes Tailwind ricos.
  - **Acceptance criteria:**
    - [x] Mapeia títulos `h1`-`h4`, parágrafos, listas `ul`/`ol`, citações `blockquote`, links `a`.
    - [x] Mapeia tabelas `table`, `thead`, `th`, `td` dentro de container responsivo `overflow-x-auto`.
    - [x] Diferencia inline code (`code`) de bloco de código (`CodeBlock`).
  - **Verify:** `cd frontend && npm run type-check`
  - **Files:** `frontend/src/components/ui/MarkdownRenderer.tsx`

---

## Phase 3: Integration in Playground
- [x] **Task 4: Integrate MarkdownRenderer into AnswerView**
  - **Description:** Substituir a `div` com `whitespace-pre-wrap` em `AnswerView.tsx` pelo `MarkdownRenderer`.
  - **Acceptance criteria:**
    - [x] `AnswerView` renderiza markdown estruturado com títulos, listas, tabelas e blocos de código.
    - [x] Botão global de copiar a resposta inteira preservado no topo.
  - **Verify:** `cd frontend && npm run build`
  - **Files:** `frontend/src/pages/playground/AnswerView.tsx`

---

## Phase 4: Quality Gates & Verification
- [x] **Task 5: Execute Quality Gates & E2E Validation**
  - **Description:** Executar `npm run build` e `make pre-commit`, atualizar changelog e reiniciar contêineres de desenvolvimento.
  - **Acceptance criteria:**
    - [x] `npm run build` no frontend com 0 erros TypeScript / Vite.
    - [x] `make pre-commit` com 100% de sucesso.
    - [x] `CHANGELOG.md` atualizado com o Marco 1.18.
  - **Verify:** `make pre-commit`
  - **Files:** `CHANGELOG.md`, `tasks/todo.md`
