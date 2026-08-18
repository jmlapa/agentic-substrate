# 6. CQRS Consolidated Read Model & Event-Driven Projections

Data: 2026-08-17

## Status
Aceito

## Contexto
O substrato opera com **Event Sourcing** no Write Model, onde agregados (`KnowledgeBaseAggregate`) reconstroem seu estado a partir de fluxos imutáveis de eventos de domínio (`domain_events`).

No entanto, requisições de leitura HTTP na API (ex: `GET /api/v1/knowledge/bases/{id}` e `GET /api/v1/knowledge/bases`), bem como o monitoramento em tempo real do frontend console, exigem:
1. Respostas em tempo constante $O(1)$ indexadas por chave primária/estrangeira.
2. JOINs relacionais rápidos com schemas de ontologia vinculados.
3. Métricas consolidadas de documentos (contadores de chunks pai/filho, nós e arestas de grafo, flags de OCR e etapas de erro).

Fazer replay síncrono de eventos no EventStore a cada requisição de leitura HTTP gera sobrecarga computacional desnecessária e acopla a camada de apresentação ao histórico de eventos brutos.

## Decisão
Implementamos a separação formal entre **Write Model** e **Read Model** (CQRS) através do padrão **Event-Driven Projector**:
1. **Write Model:** Mantém-se 100% puro com Event Sourcing. Sagas e Comandos de escrita hidratam o agregado a partir do `EventStore.get_events()`.
2. **Event-Driven Projector (`KnowledgeBaseProjector`):** Escuta de forma assíncrona os eventos de domínio via `EventBus` e consolida atomicamente o estado nas tabelas relacionais `knowledge_bases` e `attached_documents`.
3. **Migration 0006:** Expande a tabela `attached_documents` com as colunas de OCR, contadores estruturais e metadados de erro.
4. **Read Model Repository (`PostgresKnowledgeBaseRepository`):** Realiza consultas relacionais com `LEFT JOIN ontology_templates` e agregações de documentos em $O(1)$.
5. **Backfill na Inicialização:** O `main.py` sincroniza eventos pré-existentes na inicialização da API de forma idempotente.

## Consequências
- **Positivas:**
  - Latência de leitura no frontend reduzida para $< 5ms$.
  - Desacoplamento entre evolução de eventos de domínio e formato de resposta de leitura.
  - Disponibilidade imediata do schema ontológico e métricas de grafos em endpoints `GET`.
  - Integridade garantida por transações ACID no PostgreSQL.
- **Negativas / Desafios:**
  - Necessidade de manter a idempotência nos handlers do projetor (`ON CONFLICT DO UPDATE`).
