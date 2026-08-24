# Spec: Smart Notes Portal & Document Explorer (Marco 1.18)

## 1. Objective & Scope

Prover uma interface de leitura e exploração rica de notas e documentos parseados (estilo Notion / GitBook / Obsidian simplificado), permitindo ao usuário navegar de forma estruturada pelo conteúdo em Markdown, localizar notas rapidamente via Command Palette (`Ctrl+K`), e interagir com um assistente de IA com escopo no documento aberto ou em toda a Knowledge Base.

### Decisões Arquiteturais Direcionadas (Maior Impacto, Menor Complexidade)
- **Modo Read-Only Especializado:** Foco estrito em leitura, busca e perguntas ao LLM. Sem suporte a edição WYSIWYG manual em v1 para evitar complexidade desproporcional de sincronização e concorrência.
- **Leitura Direta O(1) de Storage:** O Markdown canônico é servido diretamente do `IObjectStorage` (`{partition}/markdown/{doc_id}.md`) com metadados do Postgres Read Model.
- **RAG com Escopo por Documento Unificado:** Extensão do `QueryKnowledgeUseCase` existente com o parâmetro opcional `document_id`, filtrando a busca vetorial via Cypher no FalkorDB sem duplicar código de síntese.
- **Command Palette Rápido (`Ctrl+K`):** Busca instantânea por correspondência textual nos documentos e cabeçalhos cadastrados no Postgres com debounce de 200ms.
- **Sumário Interativo com Scroll Spy:** Geração determinística de âncoras para cabeçalhos (`h1`-`h4`) via slugging nativo e rastreamento de posição por `IntersectionObserver`.

---

## 2. Tech Stack & Dependencies

- **Backend:** Python 3.12+, FastAPI, Pydantic v2, PostgreSQL (asyncpg), FalkorDB (Cypher), Object Storage.
- **Frontend:** React 18.3+, TypeScript (strict), Vite, Tailwind CSS 3.4+, Lucide React, `react-markdown`, `remark-gfm`, `@tailwindcss/typography`.
- **Qualidade & Gates:** Mypy (strict), Ruff, Pytest (100% async).

---

## 3. Backend Architecture & Contracts

### 3.1 Estrutura de Arquivos (Regra: Single Class per File)

```
src/
├── api_gateway/
│   ├── dtos/
│   │   ├── get_document_content_dto.py
│   │   └── quick_search_dto.py
│   └── controllers/
│       └── knowledge_controller.py                     # Novos endpoints registrados
└── modules/knowledge/
    └── application/
        └── use_cases/
            ├── get_document_content/
            │   ├── __init__.py
            │   ├── get_document_content_request.py
            │   ├── get_document_content_response.py
            │   └── get_document_content_use_case.py
            └── quick_search_notes/
                ├── __init__.py
                ├── quick_search_notes_request.py
                ├── quick_search_notes_response.py
                └── quick_search_notes_use_case.py
```

---

### 3.2 Contratos de API REST

#### A. Obter Conteúdo da Nota (`GET /api/v1/knowledge/bases/{kb_id}/documents/{doc_id}/content`)
Retorna o Markdown canônico, metadados do documento e a hierarquia de cabeçalhos (ToC).

**Response (200 OK):**
```json
{
  "document_id": "8f8832a7-526e-425d-bb27-7cfd90069352",
  "kb_id": "c1f7b036-7c98-4682-84da-5fec8a42c0c7",
  "file_name": "Relatorio_Arquitetura.pdf",
  "source_type": "document",
  "status": "INDEXED",
  "total_parents": 8,
  "total_children": 24,
  "markdown_content": "# 1. Visão Geral da Arquitetura\n\nEste documento detalha o pipeline...\n\n## 1.1 Storage Canônico\n...",
  "toc_tree": [
    { "level": 1, "title": "1. Visão Geral da Arquitetura", "anchor": "1-visao-geral-da-arquitetura" },
    { "level": 2, "title": "1.1 Storage Canônico", "anchor": "11-storage-canonico" }
  ],
  "ingested_at": 1740354000.0
}
```

#### B. Busca Global Rápida (`GET /api/v1/knowledge/bases/{kb_id}/quick-search?q={query}`)
Utilizado pelo Command Palette (`Ctrl+K`) para navegação em tempo real.

**Response (200 OK):**
```json
{
  "query": "storage",
  "results": [
    {
      "document_id": "8f8832a7-526e-425d-bb27-7cfd90069352",
      "document_name": "Relatorio_Arquitetura.pdf",
      "match_type": "header",
      "matched_title": "1.1 Storage Canônico",
      "anchor": "11-storage-canonico",
      "preview": "O armazenamento canônico é feito através do protocolo IObjectStorage..."
    }
  ]
}
```

#### C. Extensão do Endpoint RAG (`POST /api/v1/knowledge/bases/{kb_id}/query`)
Adiciona suporte ao filtro estrito por `document_id`.

**Payload atualizado (`QueryKnowledgeDTO`):**
```json
{
  "query": "Quais são as principais restrições de concorrência?",
  "document_id": "8f8832a7-526e-425d-bb27-7cfd90069352",
  "mode": "synthesis",
  "top_k": 5
}
```

**Alteração na consulta Cypher do `FalkorDbGraphStoreAdapter`:**
```cypher
CALL db.idx.vector.queryNodes('ChildChunk', 'embedding', $candidate_k, vecf32($query_vec))
YIELD node AS child, score AS vec_score
MATCH (p_seed:ParentChunk)-[:CONTAINS_CHILD]->(child)
WHERE ($doc_id IS NULL OR p_seed.document_id = $doc_id)
WITH p_seed, max(1.0 - vec_score) AS seed_score
...
```

---

## 4. Frontend Architecture & UI Components

### 4.1 Estrutura de Módulos no Frontend

```
frontend/src/
├── api/
│   ├── knowledge-api.ts                                # Novos métodos: getDocumentContent, quickSearchNotes
│   └── types.ts                                        # Tipos: DocumentContentResponse, QuickSearchResult, TocItem
├── components/
│   └── notes/
│       ├── NotesSidebarTree.tsx                        # Árvore de navegação retrátil de KBs e Documentos
│       ├── TableOfContents.tsx                         # Outliner com ScrollSpy interativo
│       ├── CommandPaletteModal.tsx                     # Modal global acionado por Ctrl+K / Cmd+K
│       └── DocumentChatDrawer.tsx                      # Painel lateral retrátil de chat com IA e seletor de escopo
└── pages/
    └── notes/
        └── NotesPortalPage.tsx                         # Layout principal integrado do portal de notas
```

---

## 5. Plano de Implementação Incremental

1. **Passo 1 (Backend Core):** Criar `GetDocumentContentUseCase`, `QuickSearchNotesUseCase` e estender `QueryKnowledgeUseCase` com `document_id`.
2. **Passo 2 (FalkorDB Adapter):** Ajustar a query Cypher em `FalkorDbGraphStoreAdapter` para aplicar o filtro `$doc_id` quando fornecido.
3. **Passo 3 (API Gateway):** Expor as rotas no `knowledge_controller.py` e mapear os DTOs.
4. **Passo 4 (Frontend API & Types):** Adicionar chamadas no `knowledge-api.ts` e contratos em `types.ts`.
5. **Passo 5 (Frontend UI - Outliner & Leitor):** Implementar `NotesSidebarTree`, `TableOfContents` com ScrollSpy e `NotesPortalPage`.
6. **Passo 6 (Frontend UI - Command Palette & Chat Drawer):** Implementar atalho global `Ctrl+K` em `CommandPaletteModal` e o assistente contextual `DocumentChatDrawer`.
7. **Passo 7 (Testes & Validação):** Executar bateria de testes automatizados com `make pre-commit`.

---

## 6. Critérios de Aceite

- [ ] Usuário consegue acessar a rota `/notes` e selecionar qualquer documento ingerido para visualização formatada.
- [ ] O Markdown renderiza perfeitamente tabelas GFM, checklists, blocos de código com botão de cópia e cabeçalhos.
- [ ] O sumário lateral (ToC) destaca a seção ativa conforme o usuário rola a página e salta para o cabeçalho ao ser clicado.
- [ ] O atalho `Ctrl+K` (ou `Cmd+K`) abre o Command Palette instantaneamente permitindo buscar e abrir qualquer nota.
- [ ] O assistente de IA responde perguntas com precisão restrita ao documento aberto quando configurado em `Documento Atual`, e expande para a KB quando alternado para `Toda a Base`.
- [ ] Todos os gates de qualidade (`make pre-commit`, `mypy --strict`, `ruff check`, `pytest`) passam com zero erros.
