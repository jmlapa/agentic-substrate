# Implementation Plan: Marco 1.18 — Rich Markdown Renderer for RAG Playground

## 1. Context & Objectives
O Playground do Agentic Substrate recebe respostas fact-dense sintetizadas por LLM (Gemma 4 / DeepSeek V4) ricas em estruturas de Markdown (código Python/SQL/Cypher, tabelas comparativas, listas hierárquicas, títulos e citações). Atualmente, o componente `AnswerView.tsx` apenas exibe o texto bruto dentro de uma `div` com `whitespace-pre-wrap`, resultando em uma experiência visual pobre e sem destaque de sintaxe ou tabelas formatadas.

O objetivo do Marco 1.18 é introduzir uma camada completa e moderna de renderização Markdown no frontend com `react-markdown`, `remark-gfm`, `@tailwindcss/typography` e componentes Tailwind customizados para cada elemento.

---

## 2. Proposed Architecture & Component Design

```
                     ┌───────────────────────────────┐
                     │    QueryPlaygroundView.tsx    │
                     └───────────────┬───────────────┘
                                     │
                     ┌───────────────▼───────────────┐
                     │        AnswerView.tsx         │
                     └───────────────┬───────────────┘
                                     │
                     ┌───────────────▼───────────────┐
                     │     MarkdownRenderer.tsx      │
                     │  (ReactMarkdown + remarkGfm)  │
                     └───────────────┬───────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
      ┌──────────▼──────────┐                 ┌──────────▼──────────┐
      │    CodeBlock.tsx    │                 │   HTML / GFM Tags   │
      │ (Lang badge + copy) │                 │  (Table, Quote, ...) │
      └─────────────────────┘                 └─────────────────────┘
```

---

## 3. Phased Implementation Plan

### Phase 1: Package Dependencies & Tailwind Configuration
- Instalar `react-markdown`, `remark-gfm` e `@tailwindcss/typography` no package do frontend.
- Configurar o plugin `@tailwindcss/typography` no `frontend/tailwind.config.js`.

### Phase 2: Core Markdown Components
- Criar `frontend/src/components/ui/CodeBlock.tsx`:
  - Extração inteligente de linguagem (`language-python`, `language-sql`, etc.).
  - Header superior com badge da linguagem e botão "Copiar código" com ícone `Check` de feedback.
  - Scroll horizontal e container com contraste visual elevado (`bg-zinc-950/90 border border-zinc-800`).
- Criar `frontend/src/components/ui/MarkdownRenderer.tsx`:
  - Mapeamento completo de componentes:
    - `h1`, `h2`, `h3`, `h4`: títulos escuros semânticos.
    - `p`: parágrafos com `leading-relaxed` e `text-zinc-200`.
    - `ul`, `ol`, `li`: listas com recuo e marcadores estilizados.
    - `blockquote`: barra lateral de destaque indigo/emerald.
    - `table`, `thead`, `tbody`, `tr`, `th`, `td`: tabelas completas com container responsivo e scroll horizontal.
    - `code`: delegação inteligente (inline code styled vs `CodeBlock`).
    - `a`: links externos com `target="_blank"` e hover estilizado.

### Phase 3: Integration into Playground & Evidence Viewers
- Atualizar `frontend/src/pages/playground/AnswerView.tsx` para substituir `whitespace-pre-wrap` pelo `MarkdownRenderer`.
- Opcionalmente estender o visualizador de chunks (`EvidenceInspector.tsx`) para snippets markdown estruturados.

### Phase 4: Verification & Quality Gates
- Executar `npm run build` no `frontend/` validando 100% de conformidade de tipagem TypeScript.
- Executar `make pre-commit` para validar todo o repositório.
