# Spec: Rich Markdown Renderer for RAG Playground

## Objective
Prover uma renderização rica, moderna, segura e com formatação perfeita para as respostas sintetizadas de RAG no Playground (`QueryPlaygroundView` e `AnswerView`). A visualização deve suportar GitHub Flavored Markdown (GFM) completo (tabelas, listas de tarefas, strikethrough, autolinks), blocos de código com destaque de sintaxe e botão de cópia rápida, tipografia escura calibrada, citações (`> [!NOTE]`, etc.), tabelas estilizadas e inline code formatado.

---

## Tech Stack & Dependencies
- **React:** 18.3.1 + TypeScript (strict)
- **Vite:** 5.4.9
- **Tailwind CSS:** 3.4.14
- **Markdown Core:** `react-markdown` (^9.x)
- **Plugins:**
  - `remark-gfm` (^4.x) para suporte a tabelas GFM, checklists e formatação avançada.
  - `@tailwindcss/typography` (^0.5.x) para suporte a classes `prose` e `prose-invert`.
- **Icons:** `lucide-react` (ícones de cópia, código, check, link externo, etc.).

---

## Commands
```bash
# Instalação de dependências no frontend
cd frontend && npm install react-markdown remark-gfm @tailwindcss/typography

# Build e verificação de tipagem
cd frontend && npm run build

# Validação do repositório
make pre-commit
```

---

## Project Structure
```
frontend/
├── tailwind.config.js                                  # Habilitar plugin @tailwindcss/typography
├── src/
│   ├── components/
│   │   └── ui/
│   │       ├── MarkdownRenderer.tsx                    # Componente desacoplado e reutilizável de renderização Markdown
│   │       └── CodeBlock.tsx                           # Subcomponente para renderizar blocos de código com syntax/copy
│   └── pages/
│       └── playground/
│           ├── AnswerView.tsx                          # Consumidor do MarkdownRenderer para síntese RAG
│           └── EvidenceInspector.tsx                   # Renderização de snippets markdown nos chunks de evidência
```

---

## UI/UX & Component Design

### 1. `MarkdownRenderer.tsx`
Componente central que encapsula o `ReactMarkdown` com `remarkGfm` e mapeia tags HTML para componentes Tailwind enriquecidos:
- **Headings (`h1`, `h2`, `h3`, `h4`):** Tipografia semântica, cores claras (`text-zinc-100`), espaçamento vertical proporcional e bordas sutis para `h1`/`h2`.
- **Parágrafos (`p`):** `leading-relaxed`, espaçamento `mb-3`, contraste de texto `text-zinc-200`.
- **Listas (`ul`, `ol`, `li`):** Marcadores estilizados (`list-disc`, `list-decimal`), alinhamento preciso, suporte a task lists (`[x]`, `[ ]`).
- **Blocos de Código (`pre`, `code`):**
  - Inline `code`: `bg-zinc-800/90 text-indigo-300 px-1.5 py-0.5 rounded font-mono text-xs border border-zinc-700/50`.
  - Fenced code blocks (`pre`): Card escuro com header exibindo o nome da linguagem e botão de copiar individual com feedback tátil de 2 segundos.
- **Tabelas (`table`, `thead`, `tbody`, `tr`, `th`, `td`):**
  - Container responsivo com scroll horizontal suave (`overflow-x-auto`).
  - Cabeçalhos escuros com texto em negrito (`bg-zinc-800/80 text-zinc-200`).
  - Linhas com bordas delicadas (`border-zinc-800`) e hover suave (`hover:bg-zinc-800/30`).
- **Blockquotes (`blockquote`):** Borda esquerda colorida (`border-l-4 border-indigo-500 bg-indigo-950/20 px-4 py-2 rounded-r italic text-zinc-300`).
- **Links (`a`):** `text-indigo-400 hover:text-indigo-300 underline underline-offset-2`, `target="_blank"`, `rel="noopener noreferrer"`.
- **Separadores (`hr`):** `border-zinc-800 my-4`.

### 2. `AnswerView.tsx`
- Remove `whitespace-pre-wrap` manual e integra o `MarkdownRenderer`.
- Mantém o botão principal de copiar a resposta completa no topo.
- Preserva o cabeçalho de proveniência e modelo (Gemma 4 / DeepSeek).

---

## Testing Strategy
- **Type Checking:** `npm run build` (`tsc && vite build`) garantindo zero erros de tipagem TypeScript no modo estrito.
- **Visual & Component Regression:** Verificação de renderização com exemplos variados de Markdown (código Python/SQL, listas, tabelas, blockquotes, inline formatting).
- **Zero Errors CI:** `make pre-commit` validando todo o backend e frontend.

---

## Boundaries
- **Always:**
  - Sanitizar/prevenir execução arbitrária de scripts inseguros (o `react-markdown` não usa `dangerouslySetInnerHTML` por padrão).
  - Usar Single Component per File (`MarkdownRenderer.tsx`, `CodeBlock.tsx`, etc.).
  - Manter tema dark consistente com a paleta Tailwind do projeto (`zinc-900`, `indigo-500`, `emerald-400`).
- **Ask first:** Adicionar novas bibliotecas de renderização pesadas (ex: bibliotecas full WASM de syntax highlight > 5MB).
- **Never:** Renderizar Markdown via `dangerouslySetInnerHTML` com HTML não higienizado.

---

## Success Criteria
1. O Playground RAG renderiza respostas sintetizadas com formatação visualmente rica: títulos, negritos, itálicos, tabelas, listas numeradas e bullet points perfeitamente alinhados.
2. Blocos de código possuem destaque visual escuro, tag de identificação da linguagem e botão individual de cópia com feedback visual.
3. Tabelas em Markdown são renderizadas como tabelas HTML responsivas e bem formatadas.
4. `npm run build` no frontend e `make pre-commit` executam com 100% de sucesso.
