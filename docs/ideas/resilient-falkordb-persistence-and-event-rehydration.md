# Resilient FalkorDB Persistence & Event-Driven Graph Rehydration

## Problem Statement
Como garantir que os grafos de conhecimento e índices vetoriais no FalkorDB sobrevivam a reinicializações de contêineres e falhas de infraestrutura, com recuperação determinística e custo zero de LLM?

## Recommended Direction
Adotamos uma estratégia em dois níveis de resiliência:
1. **Nível 1 (Persistência Nativa do Docker/FalkorDB):**
   - Correção do ponto de montagem do volume para o diretório `/data` do contêiner.
   - Ativação do *Append-Only File (AOF)* e snapshots periódicos RDB com a diretiva `command: ["--save", "60", "1", "--appendonly", "yes", "--dir", "/data"]`.
2. **Nível 2 (Reidratação de Desastre a Custo Zero via Checkpoints):**
   - O banco relacional PostgreSQL (Event Store) permanece como a única fonte de verdade imutável.
   - Como os checkpoints de grafos (`graph_cache/{doc_id}/`) e chunks estruturais (`chunks/{doc_id}_chunks.json`) já são gravados no storage local em disco durante a ingestão, o grafo pode ser reconstruído integralmente no FalkorDB em caso de perda catastrófica de dados sem nenhuma chamada a APIs pagas de LLM ($0.00).

## Key Assumptions to Validate
- [x] O FalkorDB lê e grava snapshots RDB e arquivos AOF no diretório `/data`.
- [x] O volume mapeado `../data/falkordb:/data` persiste os dados no host entre paradas e inicializações (`docker compose down` e `docker compose up`).
- [ ] Implementar comando utilitário `make rehydrate-graph` ou rotina de reconciliação no startup caso o FalkorDB seja reiniciado a frio com banco vazio.

## MVP Scope
- **In Scope:**
  - Configuração do volume `/data` e flags `--save 60 1 --appendonly yes` no `docker/docker-compose.yml`.
  - Garantia de que `.gitignore` ignora `data/` para não sujar o versionamento.
- **Out of Scope (Próxima Fase):**
  - Exportação de snapshots para S3/GCS remoto.
  - Replicação mestre-escravo do FalkorDB.

## Not Doing (and Why)
- **Não persistir vetores e nós exclusivamente no PostgreSQL:** Manter a busca vetorial e ontológica unificada diretamente no FalkorDB preserva a latência sub-milissegundo da consulta em grafo Cypher.
- **Não re-executar chamadas de LLM em caso de restore:** Reconstruções de grafo utilizam estritamente o cache local estruturado gravado nas sagas de ingestão.
