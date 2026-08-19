# SPEC: Optimized GraphRAG Retrieval, Candidate Fusion & Token Budgeting

## 1. Objective & Problem Statement

O objetivo desta especificação é transformar o pipeline de recuperação do **Substrato de Conhecimento** em um motor **GraphRAG de Alta Precisão e Custo Mínimo**, solucionando simultaneamente o problema de **relevância semântica/relacional** e o risco de **inchaço descontrolado de payload (Payload Bloating / Token Waste)**.

### 1.1 Os Desafios Centrais
1. **Inchaço Multiplicativo de Contexto:** Se o usuário solicita `top_k = 3` e o grafo expande cegamente 2 vizinhos por parent mais nós anterior/posterior, o payload salta de 3 para 9–15 chunks (~9.000–15.000 tokens). Isso satura a janela de contexto de agentes autônomos no modo `retrieve` e encarece desnecessariamente a síntese.
2. **Dilemma de Seleção:** Dentre os chunks primários (vetoriais) e os chunks expandidos via relações no grafo, como determinar matematicamente quais são os mais relevantes para respeitar o orçamento estrito?
3. **Ponto Cego Vetorial:** Consultas contendo termos exatos, leis, códigos ou nomes próprios falham no embedding puro.
4. **Navegação Linear Desperdiçada:** Trazer incondicionalmente o `parent` anterior e posterior duplica o texto mesmo quando o chunk principal já continha a resposta completa.

---

## 2. Arquitetura da Solução & Decisões de Design

```
                               ┌─────────────────────────────────────────┐
                               │ POST /bases/{id}/query                  │
                               │ {query, top_k=3, mode, budget_tokens}   │
                               └────────────────────┬────────────────────┘
                                                    │
                      ┌─────────────────────────────┴─────────────────────────────┐
                      ▼                                                           ▼
         ┌─────────────────────────┐                                 ┌─────────────────────────┐
         │ 1. Vector Search (KNN)  │                                 │ 2. Entity Match (Exact) │
         │ Gemini 2 (768d Cosine)  │                                 │ Fulltext / Trigram <3ms │
         └────────────┬────────────┘                                 └────────────┬────────────┘
                      │ (Candidate Oversampling)                                  │ (Graph Anchors)
                      ▼                                                           ▼
         ┌─────────────────────────────────────────────────────────────────────────────────────┐
         │ 3. Unified Candidate & Graph Expansion Pool (FalkorDB Cypher)                       │
         │    - Primary Parents (KNN Match)                                                    │
         │    - Entity-Linked Parents ((e)<-[:MENTIONS]-(p))                                   │
         │    - 1-Hop / 2-Hop Related Parents ((p1)-[:MENTIONS]->(e)<-[:MENTIONS]-(p2))        │
         │    - Sequential Lineage IDs (prev_id, next_id - Zero Token Cost)                    │
         └──────────────────────────────────────────┬──────────────────────────────────────────┘
                                                    │
                                                    ▼
         ┌─────────────────────────────────────────────────────────────────────────────────────┐
         │ 4. Unified Re-Ranking & Dynamic Token Budgeting                                     │
         │    - Fused Score: S(P) = α·VectorScore + β·GraphProximity + γ·EntityMatch           │
         │    - Global Deduplication                                                           │
         │    - Token Budget Truncation (Garante <= top_k parents e <= max_tokens)             │
         └──────────────────────────────────────────┬──────────────────────────────────────────┘
                                                    │
                      ┌─────────────────────────────┴─────────────────────────────┐
                      ▼                                                           ▼
           mode == "retrieve"                                          mode == "synthesis"
       (Fast-Path p/ Agentes <30ms)                               (Fact-Dense Markdown DeepSeek-V4)
```

### 2.1 Estrutura do Retorno: *Expansão para Universo de 9 Candidatos & Reranking Global*

Adotamos a estratégia **Two-Stage Seed Expansion & Global Graph Reranking**:
1. **Estágio 1 (Sementes Vetoriais):** Recupera os $top\_k$ (ex: 3) `ParentChunk`s de maior similaridade vetorial via oversampling de filhos.
2. **Estágio 2 (Expansão de Subgrafo - Universo de até 9 Parents):** Para cada uma das 3 sementes, busca até 2 pais vizinhos fortemente conectados via entidades (`(p_seed)-[:MENTIONS]->(e)<-[:MENTIONS]-(p_neighbor)`), totalizando um universo expandido de até $3 + (3 \times 2) = 9$ `ParentChunk`s candidatos.
3. **Estágio 3 (Reranking Global no Universo de 9):** Todos os 9 candidatos são desduplicados e reclassificados sob o **Fused Score** (ponderando a proximidade vetorial original com o bônus de conectividade de grafo).
4. **Estágio 4 (Seleção dos $top\_k$ Campeões Absolutos):** Dentre os 9 candidatos avaliados, seleciona-se estritamente os **Top-3 com maior relevância global**.
   - *Vantagem crucial:* Se um vizinho do grafo for mais rico e relevante do que uma semente vetorial fraca, ele ultrapassa a semente no ranking e assume a vaga no $top\_k$.
5. **Navegação Linear (`PREV` / `NEXT`):**
   - **IDs e Títulos apenas por padrão (`prev_chunk_id`, `next_chunk_id`):** Custo de tokens = 0. O texto de chunks adjacentes não é anexado cegamente.

### 2.2 Algoritmo de Ranking e Fusão (Unified Hybrid Scoring)

Como o `ParentChunk` não possui embedding próprio (para evitar diluição semântica de textos longos de ~1.000 tokens), o vetor fica indexado exclusivamente nos nós `ChildChunk` (~200 tokens). O `ParentChunk` herda a pontuação do seu melhor filho recuperado no índice HNSW:

$$S_{\text{vector}}(P) = \max_{c \in \text{children}(P)} \text{Score}_{\text{HNSW}}(c)$$

Para ranquear todos os candidatos coletados (vetoriais primários, casamentos exatos de entidade e expansões de subgrafo), aplicamos a função de score unificada:

$$\text{Score}(P) = w_v \cdot S_{\text{vector}}(P) + w_e \cdot S_{\text{entity\_exact}}(P) + w_g \cdot S_{\text{graph\_density}}(P)$$

Onde:
* $w_v = 0.50$ (Similaridade semântica herdada do melhor `ChildChunk` filho).
* $w_e = 0.30$ (Casamento exato/trigram de entidades presentes na query via Fulltext).
* $w_g = 0.20$ (Densidade e centralidade de conexões ontológicas no grafo).
* **Para Parents descobertos puramente via Grafo:** Caso um `ParentChunk` vizinho seja alcançado via `(p1)-[:MENTIONS]->(e)<-[:MENTIONS]-(p2)` sem que nenhum filho seu tenha aparecido no top vetorial direto, adota-se $S_{\text{vector}}(P_2) = S_{\text{vector}}(P_1) \times \text{decay}$ (com $\text{decay} = 0.5$ para 1-hop e $0.25$ para 2-hops). Sua pontuação será impulsionada prioritariamente pelo peso relacional $S_{\text{graph\_density}}$.

---

## 3. Contratos de API & DTOs (Single Class per File)

### 3.1 DTO de Entrada: `QueryKnowledgeRequest` / `QueryKnowledgeDTO`
```python
# src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_request.py
from uuid import UUID
from pydantic import BaseModel, Field


class QueryKnowledgeRequest(BaseModel):
    kb_id: UUID
    query: str
    top_k: int = Field(
        default=3, ge=1, le=20, description="Quantidade estrita de blocos textuais principais"
    )
    mode: str = Field(
        default="synthesis",
        description="'synthesis' (Fact-Dense LLM) ou 'retrieve' (Fast-Path Agentes)",
    )
    max_tokens_budget: int = Field(
        default=3500, ge=50, le=32000, description="Teto máximo de tokens no payload (50 a 32k)"
    )
    include_graph_triples: bool = Field(
        default=True, description="Inclui triplas relacionais estruturadas de alta certeza"
    )
```


### 3.2 Value Object de Resultado: `HybridSearchResult`
```python
# src/modules/knowledge/domain/value_objects/hybrid_search_result.py
from typing import Any
from pydantic import Field
from src.kernel.domain.value_object import ValueObject


class HybridSearchResult(ValueObject):
    parent_chunk_id: str
    document_id: str
    document_name: str
    header_path: str
    parent_content: str
    relevance_score: float
    retrieval_source: str = Field(
        description="'vector_match' | 'entity_fulltext' | 'graph_expansion'"
    )
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None
    related_triples: list[str] = Field(
        default_factory=list, description="Triplas estruturadas: ['A -> REVOGA -> B']"
    )
    related_entities: list[dict[str, Any]] = Field(default_factory=list)
```

### 3.3 DTO de Resposta: `QueryKnowledgeResponse`
```python
# src/modules/knowledge/application/use_cases/query_knowledge/query_knowledge_response.py
from pydantic import BaseModel, Field
from src.modules.knowledge.domain.value_objects.hybrid_search_result import HybridSearchResult


class QueryKnowledgeResponse(BaseModel):
    answer: str = Field(
        default="", description="Síntese Fact-Dense em Markdown ou resumo do retrieve"
    )
    results: list[HybridSearchResult] = Field(
        default_factory=list, description="Lista estrita de até top_k evidências"
    )
    total_tokens_estimated: int = Field(
        default=0, description="Estimativa de tokens consumidos pelo payload"
    )
    matched_entities_in_query: list[str] = Field(
        default_factory=list, description="Entidades detectadas via Zero-Token Linking"
    )
```

---

## 4. Query Cypher Unificada de Alta Eficiência (FalkorDB)

A consulta é executada em uma **única transação atômica** no FalkorDB, combinando busca vetorial com oversampling ($candidate\_k = \max(top\_k \times 4, 50)$), deduplicação natural de todos os `ParentChunk`s derivados dos filhos (sem afunilamento precoce), expansão de até 5 vizinhos ontológicos por semente e reranking global pelo `FusedScore`:

```cypher
// 1. Sementes Vetoriais com Oversampling de Filhos (candidate_k = max(top_k * 4, 50))
CALL db.idx.vector.queryNodes('ChildChunk', 'embedding', $candidate_k, vecf32($query_vec)) 
YIELD node AS child, score AS vec_score
MATCH (p_seed:ParentChunk)-[:CONTAINS_CHILD]->(child)
WITH p_seed, max(1.0 - vec_score) AS seed_score
ORDER BY seed_score DESC

// 2. Expansão de Subgrafo: busca até 5 vizinhos por semente via entidades ontológicas dinâmicas
OPTIONAL MATCH (p_seed)-[:MENTIONS]->(e)<-[:MENTIONS]-(p_neighbor:ParentChunk)
WHERE p_neighbor <> p_seed
WITH p_seed, seed_score, p_neighbor, count(DISTINCT e) AS shared_entities
ORDER BY shared_entities DESC
WITH p_seed, seed_score, collect(DISTINCT {parent: p_neighbor, shared_entities: shared_entities})[0..5] AS top_neighbors

// 3. Montagem do Universo de Candidatos
UNWIND (CASE WHEN size(top_neighbors) > 0 THEN top_neighbors 
             ELSE [{parent: null, shared_entities: 0}] END) AS tn
WITH collect(DISTINCT {parent: p_seed, base_score: seed_score, is_seed: true, shared_entities: 0}) + 
     collect(DISTINCT {parent: tn.parent, base_score: seed_score * 0.7, is_seed: false, shared_entities: tn.shared_entities}) AS raw_candidates
UNWIND raw_candidates AS c
WITH c.parent AS p, max(c.base_score) AS base_score, max(c.shared_entities) AS shared_entities, max(c.is_seed) AS is_seed
WHERE p IS NOT NULL

// 4. Reranking Global Unificado (Bounded Multiplicative Decay)
WITH p,
     CASE WHEN is_seed THEN base_score 
          ELSE (base_score * (1.0 + (CASE WHEN shared_entities > 5 THEN 5 ELSE shared_entities END * 0.05)))
     END AS fused_score,
     is_seed
ORDER BY fused_score DESC
LIMIT $top_k  // <-- Único corte de LIMIT, garantindo a seleção dos TOP K campeões absolutos

// 5. Coleta de Triplas, Entidades e Navegação Linear dos Campeões
OPTIONAL MATCH (p)-[:MENTIONS]->(e1)
OPTIONAL MATCH (e1)-[r]->(e2)
MATCH (d:Document)-[:HAS_PARENT]->(p)
OPTIONAL MATCH (p)-[:NEXT]->(next_p:ParentChunk)
OPTIONAL MATCH (prev_p:ParentChunk)-[:NEXT]->(p)

RETURN p.id AS parent_id,
       coalesce(d.id, '') AS document_id,
       coalesce(d.name, '') AS document_name,
       p.header_path AS header_path,
       p.content AS parent_content,
       fused_score AS relevance_score,
       prev_p.id AS prev_chunk_id,
       next_p.id AS next_chunk_id,
       is_seed AS is_seed,
       collect(DISTINCT CASE WHEN e1 IS NOT NULL AND r IS NOT NULL AND e2 IS NOT NULL 
            THEN (coalesce(e1.name, e1.id, '') + ' ' + type(r) + ' ' + coalesce(e2.name, e2.id, '')) 
            ELSE null END)[0..5] AS related_triples,
       collect(DISTINCT {type: labels(e1)[0], properties: properties(e1)}) AS related_entities
ORDER BY relevance_score DESC
```

---

## 5. Token Budgeting & Formatação de Síntese

### 5.1 Dynamic Token Budgeting no `QueryKnowledgeUseCase`
Antes de despachar o resultado para a API ou para a LLM, o caso de uso realiza o corte dinâmico de orçamento:
1. Calcula a contagem estimada de tokens: $\text{Tokens} \approx \frac{\text{len}(\text{content})}{3.3}$.
2. Se a soma dos $top\_k$ chunks ultrapassar `max_tokens_budget` (default 3.500 tokens, máximo 32.000 tokens), o caso de uso mantém a integridade do chunk #1 e aplica truncamento inteligente nas seções secundárias dos chunks inferiores, descartando fragmentos menores que 50 tokens.

### 5.2 Formatação Fact-Dense e Defesa de Injeção no `OpenRouterRagSynthesizer` (Gemma 4)
O prompt injeta os blocos de evidência acompanhados das triplas estruturadas e encapsulados em tags XML:

```xml
<evidence id="parent_123" document="contrato.pdf" section="# 4.1 Rescisão" score="0.9600">
  <structured_facts>
    <triple>Empresa X CONTRATADA_POR Órgão Y</triple>
  </structured_facts>
  <content>
    O atraso superior a 60 dias autoriza a rescisão unilateral...
  </content>
</evidence>
```


---

## 6. Project Structure (Single Class per File)

```
src/modules/knowledge/
├── domain/
│   ├── interfaces/
│   │   ├── i_graph_store.py                     # Atualizado com assinatura de query otimizada e budget
│   │   ├── i_embedding_service.py               # Interface Gemini 2 (768d)
│   │   └── i_llm_synthesis_service.py           # Interface de síntese Fact-Dense
│   └── value_objects/
│       └── hybrid_search_result.py              # Value object enriquecido com triplas, prev/next IDs e source
├── infrastructure/
│   └── adapters/
│       ├── falkordb_graph_store_adapter.py      # Implementação Cypher com candidate oversampling e fusão
│       ├── in_memory_graph_store.py             # Mock in-memory com suporte a scoring e prev/next
│       └── deepseek_rag_synthesizer.py          # Sintetizador OpenRouter com injeção de triplas relacionais
└── application/
    └── use_cases/
        └── query_knowledge/
            ├── query_knowledge_request.py       # DTO com top_k estrito e max_tokens_budget
            ├── query_knowledge_response.py      # DTO com answer, results, total_tokens_estimated
            └── query_knowledge_use_case.py      # Orquestrador de busca, fusão, budgeting e síntese
```

---

## 7. Boundaries & Quality Rules

- **Always:**
  - Manter 1 classe por arquivo em todas as camadas.
  - Executar `make pre-commit` e garantir zero erros no Mypy (`strict = true`) e Ruff.
  - Garantir que o array `results` NUNCA exceda `request.top_k` itens.
  - Não enviar o texto completo de chunks anteriores/posteriores por padrão (apenas IDs).
- **Never:**
  - Chamar LLM para extrair entidades de queries no modo `retrieve` (usar apenas Fulltext/Trigram no grafo).
  - Permitir vazamento de tokens que exceda `max_tokens_budget`.
- **Ask First:**
  - Alterações nos pesos da fórmula de score ponderado ($w_v, w_e, w_g$).

---

## 8. Success Criteria

- [ ] A consulta com `top_k=3` retorna estritamente **3 `ParentChunk`s distintos** mesmo se múltiplos filhos pertencerem ao mesmo pai.
- [ ] A busca vetorial utiliza candidate oversampling ($k_{\text{cand}} = \max(top\_k \times 4, 20)$).
- [ ] Triplas relacionais do grafo são anexadas sem duplicar blocos de texto.
- [ ] O modo `retrieve` responde em **< 30ms** com 0 tokens de LLM consumidos.
- [ ] O payload total respeita rigorosamente o `max_tokens_budget`.
- [ ] 100% dos testes unitários e de integração passando no Pytest.
- [ ] `make pre-commit` executado com sucesso.
