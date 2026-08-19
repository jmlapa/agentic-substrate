# ADR-0009: Bounded Multiplicative Graph Decay, Natural Candidate Deduplication & Asymmetric Retrieval for FalkorDB GraphRAG

## Status
Accepted (Amends and supersedes the candidate fusion section of [ADR-0008](file:///Users/insider/personal/agentic-substrate/docs/decisions/0008-optimized-graphrag-retrieval-and-budgeting.md))

## Date
2026-08-19

## Context
1. **Invariância de Top-1 e Afunilamento Precoce de Sementes (*Seed Pool Starvation*)**:
   Na implementação original do [ADR-0008](file:///Users/insider/personal/agentic-substrate/docs/decisions/0008-optimized-graphrag-retrieval-and-budgeting.md), a consulta Cypher aplicava um corte intermediário `LIMIT $top_k` imediatamente após o agrupamento das sementes vetoriais (`WITH p_seed, max(1.0 - vec_score)`). Quando o usuário solicitava `top_k=1`, apenas uma única semente era retida antes da expansão de vizinhos (`[:MENTIONS]`), impedindo a descoberta de nós altamente conectados vinculados à 2ª ou 3ª melhor semente. Isso causava uma anomalia em que `top_k=5` trazia um resultado #1 muito mais relevante do que `top_k=1`.
2. **Distorção de Nós Hub e Índices Remissivos por Soma Aditiva Descalibrada**:
   A fórmula anterior `fused_score = base_score + (shared_entities * 0.10)` combinava diretamente grandezas de escalas incompatíveis: similaridade de cosseno restrita a $[0, 1]$ com contagem de entidades compartilhadas em números inteiros ($4, 5, 6\dots$). Em documentos legais e técnicos extensos (como a Constituição Federal), páginas de **Índice Remissivo Alfabético** e glossários mencionam centenas de entidades genéricas (`União`, `STF`, `Constituição`). Ao acumular 4 a 6 entidades compartilhadas, esses índices ganhavam $+0.40$ a $+0.60$ de bônus puro, saltando de score $0.67$ para $1.07+$ e ultrapassando textos normativos diretos de altíssima relevância vetorial (como o Artigo 170 com score $0.8052$).
3. **Alinhamento Vetorial Assimétrico**:
   O caso de uso de consulta (`QueryKnowledgeUseCase`) invocava o método simétrico `embed_texts([query])` em vez da diretiva de busca assimétrica `embed_query(query)` (`task: search result | query: ...`) otimizada para perguntas e respostas no Gemini 2.

## Decision
1. **Deduplicação Natural de Sementes com Oversampling $candidate\_k = \max(top\_k \times 4, 50)$**:
   - Remoção do `LIMIT` intermediário na fase de sementes no Cypher.
   - O índice vetorial HNSW consulta $candidate\_k \ge 50$ nós `ChildChunk`, e todos os nós `ParentChunk` derivados são deduplicados naturalmente na tabela hash in-memory do FalkorDB.
2. **Expansão Ampliada de Vizinhos ($[0..5]$)**:
   - Cada semente no grafo expande até **5 vizinhos ontológicos mais conectados** através de entidades conceituais compartilhadas (`[0..5]`).
3. **Reranking com *Bounded Multiplicative Graph Decay***:
   - **Sementes Vetoriais Diretas:** Mantêm seu score de similaridade real de cosseno ($1.0 - distance$), preservando a soberania semântica do match direto.
   - **Vizinhos de Grafo:** Entram com fator de decaimento de distância de salto ($0.70\times$ do score da semente originária) e recebem um reforço proporcional limitado ($\le 25\%$):
     $$\text{FusedScore}_{\text{neighbor}} = (\text{SeedScore} \times 0.70) \times (1.0 + \min(\text{shared}, 5) \times 0.05)$$
   - Um único corte `LIMIT $top_k` é aplicado estritamente no encerramento da consulta Cypher após o ordenamento global por `fused_score DESC`.
4. **Busca Assimétrica Oficial (`embed_query`)**:
   - `QueryKnowledgeUseCase` padronizado para chamar `IEmbeddingService.embed_query(request.query)`.

## Cypher Query Unificada Oficial (FalkorDB)
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
LIMIT $top_k

// 5. Coleta de Triplas, Entidades (Null-Safe) e Navegação Linear
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
       collect(DISTINCT CASE WHEN e1 IS NOT NULL THEN {type: labels(e1)[0], properties: properties(e1)} ELSE null END) AS related_entities
ORDER BY relevance_score DESC
```

## Consequences
- **Invariância de Top-1**: O resultado #1 retornado com `top_k=1`, `top_k=5` ou `top_k=10` é matematicamente idêntico e consistente.
- **Imunidade a Nós Hub e Índices**: Páginas de sumário e índices alfabéticos não mais ultrapassam correspondências semânticas substantivas de alta pontuação vetorial.
- **Preservação de Latência Sub-5ms**: Todo o pipeline de recuperação continua executando em uma única transação atômica em memória no FalkorDB.
