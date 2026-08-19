# ADR-0008: Optimized GraphRAG Retrieval, Candidate Fusion & Dynamic Token Budgeting

## Status
Accepted (Candidate fusion & scoring amended by [ADR-0009](file:///Users/insider/personal/agentic-substrate/docs/decisions/0009-bounded-multiplicative-graph-decay-and-natural-deduplication.md))

## Date
2026-08-18

## Context
1. **Recuperação Fragmentada e Custo de Janela**: Em queries complexas, trazer apenas os chunks vetoriais imediatos (`seed_chunks`) ignorava o contexto estrutural (pais adjacentes no documento) e nós vizinhos altamente relacionados no grafo de conhecimento.
2. **Fanout Descontrolado de Grafo**: Expandir todos os vizinhos conectados a entidades populares causava explosão combinatória de candidatos e estouro de tokens no LLM.
3. **Injeção de Prompts Indireta (Indirect Prompt Injection)**: Chunks formatados em texto puro ou markdown simples permitiam que textos não confiáveis de documentos tentassem suplantar as instruções do sistema.
4. **Alocação Rígida de Tokens**: Chunks grandes podiam exceder a janela de contexto ou gerar micro-fragmentos ininteligíveis no prompt do LLM sintetizador (Gemma 4).

## Decision
1. **Expansão Controlada de Candidatos (Fórmula $K + 2K$)**:
   - Para um pedido de `top_k=3`, o motor FalkorDB seleciona até 3 sementes vetoriais e expande até **2 vizinhos por semente** (`collect(...)[0..2]`), gerando um pool estrito de até **9 candidatos unificados**.
2. **Fusão Global de Scores no Cypher**:
   - `fused_score = base_score + (shared_entities * 0.10)`
   - Sementes vetoriais entram com `base_score = 1.0 - vec_score` e vizinhos ontológicos entram com `base_score = seed_score * 0.70`.
3. **Navegação Sequencial entre Chunks Pais (`[:NEXT]`)**:
   - Criação em lote com `UNWIND $pairs AS pair` de arestas `(p1:ParentChunk)-[:NEXT]->(p2:ParentChunk)`.
   - Projeção de `prev_chunk_id` e `next_chunk_id` em cada `HybridSearchResult`.
4. **Dynamic Token Budgeting (Teto de 32k Tokens)**:
   - Orçamento dinâmico (`max_tokens_budget`, padrão 3.500, máximo 32.000 tokens) calculado como `math.ceil(len / 3.3)`.
   - Regra de inclusão do Chunk #1 garantida e descarte de micro-chunks abaixo de `MIN_USEFUL_TOKENS = 50`.
5. **Mitigação de Prompt Injection via Tags XML Estruturadas**:
   - O contexto entregue ao sintetizador é encapsulado em tags XML rígidas:
     `<evidence id="..." document="..." section="..." score="...">\n  <structured_facts>...</structured_facts>\n  <content>...</content>\n</evidence>`.

## Consequences
- **Precisão**: Vizinhos que compartilham múltiplas entidades conceituais são promovidos ao topo do ranking mesmo sem correspondência léxica direta.
- **Segurança**: Fronteiras XML isolam dados de documentos não confiáveis contra ataques de injeção indireta.
- **Eficiência de Custo**: Janela de contexto estritamente controlada entre 50 e 32.000 tokens com telemetria detalhada em `retrieval_trace`.
