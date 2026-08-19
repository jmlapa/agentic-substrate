# Implementation Plan: Optimized GraphRAG Retrieval, Candidate Fusion & Token Budgeting

## 1. Overview & Problem Definition
Transformar o pipeline de recuperação do **Substrato de Conhecimento** em um motor **GraphRAG de Alta Precisão e Custo Mínimo**.
O plano resolve o problema do colapso de contexto (quando múltiplos filhos pertencem ao mesmo pai) e o risco de inchaço de payload ($3 \times 2 = 6$ chunks explodindo em 12.000 tokens), implementando:
1. **Oversampling de Candidatos Filhos com Deduplicação e $top\_k$ Estrito no Pai** via Cypher atômico.
2. **Unified Scored Pool (Fused Score)** combinando similaridade vetorial herdada, casamento exato de entidades e densidade de conexões ontológicas.
3. **Metadados Estruturados Ultraleves (Triplas Semânticas & IDs de Linhagem Linear `PREV`/`NEXT`)** sem duplicar texto em prosa.
4. **Dynamic Token Budgeting Truncation** no caso de uso para garantir cumprimento rigoroso do limite de tokens (`max_tokens_budget`).

---

## 2. Architecture Decisions & Zero-Greyzone Rules

### 2.1 Herança de Vetor e Raciocínio Hierárquico
* **Decisão:** `ParentChunk` (~1.000 tokens) **NÃO** armazena embedding próprio.
* **Fórmula de Herança Vetorial:** $S_{\text{vector}}(P) = \max_{c \in \text{children}(P)} \text{Score}_{\text{HNSW}}(c)$.
* **Pais alcançados unicamente por Grafo:** Herdam o vetor atenuado com decaimento ($S_{\text{vector}}(P_2) = S_{\text{vector}}(P_1) \times 0.5$).

### 2.2 Expansão para 9 Candidatos e Reranking Global
1. **Sementes Vetoriais:** Recupera os $top\_k$ (ex: 3) `ParentChunk`s com oversampling de filhos.
2. **Expansão de Subgrafo (Até 9 Chunks):** Para cada semente, expande até 2 vizinhos via entidades compartilhadas $\rightarrow$ Universo de até $3 + (3 \times 2) = 9$ candidatos.
3. **Reranking Global:** Todos os 9 candidatos são desduplicados e classificados sob a função unificada:
   $$\text{FusedScore}(P) = \text{BaseScore}(P) + (\text{SharedEntities} \times 0.10)$$
4. **Seleção Estrita:** Seleciona estritamente os **Top-3 campeões** desse universo de 9 candidatos.
* **Garantia de Saída:** O array `results` conterá **estritamente até $top\_k$ chunks** distintos mais bem pontuados no ranking global.

### 2.3 Prevenção de Inchaço de Payload (Token Bloat Prevention)
* Lookalikes e vizinhos de grafo **NÃO** enviam parágrafos de texto duplicados. Em vez disso, enviam:
  - `related_triples: list[str]` (ex: `["EntidadeA RELACAO EntidadeB"]`) — Custo ~15 tokens.
  - `prev_chunk_id: str | None` e `next_chunk_id: str | None` — Custo 0 tokens.
* **Dynamic Token Budgeting:** Caso a soma estimada de tokens dos $top\_k$ chunks ultrapasse `max_tokens_budget` (default: 3.500 tokens), o caso de uso preserva os chunks #1 e #2 intactos e trunca suavemente o chunk #3.

---

## 3. Dependency Graph & Execution Order

```
[Domain Value Objects & Interfaces]
  │  (HybridSearchResult, IGraphStore)
  ▼
[DTOs & Controllers]
  │  (QueryKnowledgeRequest/Response, QueryKnowledgeDTO)
  ▼
[Infrastructure Adapters]
  │  (FalkorDbGraphStoreAdapter com Cypher Atômico & NEXT edges, InMemoryGraphStore)
  ▼
[Application Use Case & Synthesis]
  │  (QueryKnowledgeUseCase com Token Budgeting, DeepSeekRagSynthesizer com Triplas)
  ▼
[Verification & Quality Gate]
     (Pytest 100% Coverage, Mypy Strict, Ruff, make pre-commit)
```

---

## 4. Risks & Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Múltiplos filhos do mesmo pai derrubarem a quantidade de pais para menos de $top\_k$. | Alto | Uso obrigatório de Candidate Oversampling ($candidate\_k = \max(top\_k \times 4, 20)$) com `WITH p, max(score)` antes do `LIMIT $top_k`. |
| Inchaço de contexto em ferramentas de agentes no modo `retrieve`. | Alto | Retorno estrito de até $top\_k$ blocos textuais; triplas como strings compactas; prev/next apenas como IDs. |
| Incompatibilidade de sintaxe OpenCypher em nós sem arestas `[:NEXT]`. | Médio | Uso de `OPTIONAL MATCH` para `[:NEXT]`, `[:MENTIONS]` e `[:CONTAINS_CHILD]`. Criação de arestas `[:NEXT]` na ingestão estrutural. |
| Violação do Mypy Strict por tipos não anotados em triplas ou IDs opcionais. | Baixo | Tipagem explícita `str | None` e `list[str]` com `default_factory=list`. |

---

## 5. Implementation Phases Overview

* **Phase 1: Domain Contracts & DTOs** (Atualização de `HybridSearchResult`, `IGraphStore`, `QueryKnowledgeRequest`, `QueryKnowledgeResponse` e `QueryKnowledgeDTO`).
* **Phase 2: Graph Store & Cypher Engine** (Criação de arestas `[:NEXT]` no `store_structural_document`, nova query Cypher unificada com candidate oversampling, fusão e triplas no `FalkorDbGraphStoreAdapter` e `InMemoryGraphStore`).
* **Phase 3: Use Case Budgeting & Fact-Dense Synthesis** (Lógica de Token Budgeting no `QueryKnowledgeUseCase` e formatação de triplas no `DeepSeekRagSynthesizer`).
* **Phase 4: Test Suite & Quality Gate** (Testes unitários e de integração validando $top\_k$ estrito, triplas, prev/next IDs e execução de `make pre-commit`).
