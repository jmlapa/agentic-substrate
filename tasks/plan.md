# Plano de Implementação: Infraestrutura Local e Adaptadores de Produção (Marco 1.5)

## Visão Geral
Estruturar e implementar a camada de infraestrutura real e adaptadores locais para validação ágil do ecossistema do **Agentic Substrate** via `docker-compose.yml`. O ambiente local utilizará imagens oficiais do Docker Hub, persistência em PostgreSQL (`pgvector`), grafo em **FalkorDB**, armazenamento em **Local FileSystem** (com bind mount para o host) e parser baseado em **MarkItDown** (Microsoft).

---

## Decisões Arquiteturais e Escolhas Técnicas

1. **Object Storage -> LocalFileSystemStorageAdapter:**
   - Implementa `IObjectStorage` operando diretamente no diretório montado do host (`./data/storage`), garantindo I/O assíncrono com `aiofiles`.
   - Permite inspecionar diretamente os arquivos brutos e processados no disco local sem overhead de MinIO/S3.

2. **Parser de Documentos -> MarkItDownDocumentParser:**
   - Implementa `IDocumentParser` utilizando `markitdown` da Microsoft.
   - **Por que MarkItDown vs Docling agora:** `markitdown` é extremamente leve, inicializa instantaneamente, converte PDF, DOCX, XLSX, PPTX e HTML para Markdown limpo sem necessidade de carregar modelos pesados de Deep Learning em CPU/GPU. O `Docling` fica como candidato futuro para cenários de tabelas científicas ultra-complexas.

3. **Graph Store -> FalkorDbGraphStoreAdapter:**
   - Implementa `IGraphStore` conectando ao container oficial `falkordb/falkordb`.
   - Executa queries OpenCypher para inserção de nós/arestas com tipagem estrita da ontologia e consultas de subgrafos.

4. **Vector Store -> PgVectorStoreAdapter:**
   - Implementa `IVectorStore` conectando à extensão `pgvector` no PostgreSQL 16.
   - Criação automática da tabela de embeddings particionada por `kb_id` e busca por similaridade de cosseno com índice HNSW.

5. **Event Store -> PostgresEventStore:**
   - Implementa `EventStore` do Kernel gravando fluxos de eventos append-only na tabela `events` com concorrência otimista baseada em versão.

6. **Ambiente Local via Docker Compose:**
   - Serviços: `postgres` (`pgvector/pgvector:pg16`), `falkordb` (`falkordb/falkordb:latest`), `redis` (`redis:7-alpine`).
   - Volumes mapeados no host sob pasta `./data/`.

---

## Estrutura do Grafo de Dependências

```
docker-compose.yml (Postgres + pgvector, FalkorDB, Redis)
    │
    ├── Kernel Infrastructure: PostgresEventStore (asyncpg / sqlalchemy async)
    │
    ├── Knowledge Infrastructure: LocalFileSystemStorageAdapter (aiofiles)
    │
    ├── Knowledge Infrastructure: MarkItDownDocumentParser (markitdown)
    │
    ├── Knowledge Infrastructure: FalkorDbGraphStoreAdapter (falkordb async/client)
    │
    ├── Knowledge Infrastructure: PgVectorStoreAdapter (pgvector / asyncpg)
    │
    └── API Gateway & DI Container: Injeção dos adaptadores reais configuráveis por ambiente
```

---

## Fases de Implementação

### Fase 1: Docker Compose e Armazenamento Local
- Configurar `docker/docker-compose.yml` com Postgres+pgvector, FalkorDB, Redis e volumes no host.
- Implementar `LocalFileSystemStorageAdapter` com suporte assíncrono.
- Implementar `MarkItDownDocumentParser`.

### Ponto de Verificação 1: Storage Local & Parser
- [ ] Subida dos containers com `docker compose up -d`.
- [ ] Testes unitários e de integração do `LocalFileSystemStorageAdapter` e `MarkItDownDocumentParser`.

### Fase 2: Persistência Real (Postgres Event Store & PgVector)
- Implementar `PostgresEventStore` no `src/kernel/infrastructure/postgres_event_store.py`.
- Implementar `PgVectorStoreAdapter` no `src/modules/knowledge/infrastructure/adapters/pgvector_store_adapter.py`.
- Scripts de inicialização DDL e migrações das tabelas.

### Ponto de Verificação 2: Event Sourcing & Vetores no Postgres
- [ ] Testes de integração gravando eventos reais e recuperando histórico por `aggregate_id`.
- [ ] Testes de indexação e busca por similaridade vetorial no `pgvector`.

### Fase 3: Grafo Real (FalkorDB) e Composição de Injeção de Dependências
- Implementar `FalkorDbGraphStoreAdapter` no `src/modules/knowledge/infrastructure/adapters/falkordb_graph_store_adapter.py`.
- Atualizar o container de Injeção de Dependências (`src/api_gateway/container.py`) para alternar entre adaptadores em memória e adaptadores de infraestrutura real via variáveis de ambiente (`ENVIRONMENT=local|dev|test|prod`).

### Ponto de Verificação 3: Integração Completa Ponta a Ponta
- [ ] Pipeline completo executando com infraestrutura local real (Upload -> Storage Local -> Parser MarkItDown -> Extração Ontológica -> PgVector + FalkorDB).
- [ ] `make pre-commit` executado com 100% de sucesso.

---

## Riscos e Mitigações
| Risco | Impacto | Mitigação |
|---|---|---|
| Latência de inicialização de conexões nos adaptadores | Médio | Gerenciar pools de conexão (`asyncpg.create_pool` e FalkorDB client) no ciclo de vida da aplicação FastAPI (`lifespan`). |
| Incompatibilidade de tipos vetoriais no pgvector | Médio | Criar extensão `vector` no bootstrap do banco e registrar tipos no pool do `asyncpg`. |
| Concorrência no FileSystem local | Baixo | Utilizar diretórios particionados deterministicamente por `kb_id` e identificador do documento. |
