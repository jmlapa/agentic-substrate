# Spec: Knowledge Substrate (Marco 1 e 1.5: Kernel + Knowledge + API Gateway + Local Infra)

## Objective
Construir um substrato modular em Clean Architecture para desenvolvimento de sistemas agênticos, focado no gerenciamento de bases de conhecimento (Knowledge Bases) com GraphRAG e ontologias dinâmicas.
O sistema utiliza **Event Sourcing**, **Saga Coreografada** orientada a eventos de domínio, particionamento de storage por KB, extração estruturada de grafos baseada em **ontologias dinâmicas em runtime** (usando Pydantic v2) e persistência de dados em infraestrutura real local (Postgres + pgvector, FalkorDB, Redis e Local FileSystem Storage).

## Tech Stack
- **Linguagem:** Python 3.12+
- **Gerenciador de Dependências & Ambiente:** `uv` (`pyproject.toml`)
- **Framework Web:** FastAPI + Uvicorn (ASGI assíncrono)
- **Validação & Tipagem Dinâmica:** Pydantic v2 (`DynamicOntologyModelBuilder`)
- **Event Sourcing & Vector Store:** PostgreSQL 16 (`pgvector/pgvector:pg16`) + Driver `asyncpg` com concorrência otimista e busca por similaridade de cosseno (`<=>` com índice HNSW)
- **Object Storage:** `LocalFileSystemStorageAdapter` com bind mount em `./data/storage` e I/O assíncrono via `aiofiles`
- **Document Parser:** `MarkItDownDocumentParser` utilizando `markitdown` da Microsoft (conversão rápida de PDF, DOCX, TXT, MD sem GPU)
- **Graph Store:** `FalkorDbGraphStoreAdapter` utilizando `falkordb` e queries OpenCypher para persistência e consulta de subgrafos
- **Event Bus:** `InMemoryEventBus` (com interface desacoplada para futura expansão com Redis Pub/Sub)
- **Qualidade & Testes:** Pytest (pytest-asyncio, pytest-cov), Ruff (linter/formatter), Mypy (modo estrito: `strict = true`)

## Commands
```bash
# Sincronização de dependências
uv sync

# Subir infraestrutura local via Docker
docker compose -f docker/docker-compose.yml up -d

# Executar suíte completa de testes com cobertura
uv run pytest --cov=src --cov-report=term-missing -v

# Linter e Formatação
uv run ruff check .
uv run ruff format --check .

# Checagem de tipos estrita
uv run mypy src tests

# Gate oficial de qualidade
make pre-commit

# Executar API Gateway localmente
uv run uvicorn src.api_gateway.main:app --reload --port 8000
```

## Project Structure
```
agentic-substrate/
├── docker/
│   └── docker-compose.yml       # Postgres (pgvector), FalkorDB, Redis
├── CAPABILITY-MAP.md            # Mapa de capacidades e status dos módulos
├── SPEC-knowledge-substrate.md  # Especificação técnica do substrato
├── pyproject.toml               # Dependências e configurações de ferramentas
├── src/
│   ├── kernel/                  # Primitivas puras de Domínio e Aplicação
│   │   ├── domain/              # Entity, ValueObject, AggregateRoot, DomainEvent, DomainError, Result
│   │   ├── application/         # EventBus, EventStore, Logger, UseCase
│   │   └── infrastructure/      # PostgresEventStore, InMemoryEventStore, InMemoryEventBus
│   │
│   ├── modules/
│   │   └── knowledge/           # Módulo GraphRAG & Knowledge Base
│   │       ├── domain/          # KnowledgeBase, Document, OntologyTemplate, OntologySchema, GraphNode, GraphEdge
│   │       │   ├── interfaces/  # IKnowledgeBaseRepository, IOntologyRepository, IObjectStorage, IDocumentParser, IVectorStore, IGraphStore, IGraphExtractor
│   │       │   ├── value_objects/
│   │       │   └── events/      # Eventos de domínio do ciclo de vida da KB e documentos
│   │       ├── application/     # Sagas e Casos de Uso
│   │       │   ├── sagas/       # DocumentIngestionSagaCoordinator
│   │       │   └── use_cases/   # CreateKnowledgeBase, AttachAndStoreDocument, QueryKnowledge, CreateOntology, GetOntology, ListOntologies
│   │       └── infrastructure/  # Adaptadores reais e extratores
│   │           ├── adapters/    # LocalFileSystemStorageAdapter, MarkItDownDocumentParser, PgVectorStoreAdapter, FalkorDbGraphStoreAdapter, InMemory repos/stores
│   │           └── extractors/  # DynamicOntologyModelBuilder, StructuredPydanticGraphExtractor
│   │
│   └── api_gateway/             # Exposição HTTP / REST
│       ├── controllers/         # KnowledgeController, OntologyController
│       ├── dtos/                # DTOs tipados (Request/Response)
│       ├── container.py         # Container IoC / Injeção de dependências configurável
│       └── main.py              # Aplicação FastAPI e rotas
└── tests/
    ├── unit/                    # Testes de unidade de domínio, use cases e adaptadores
    └── integration/             # Testes de integração (API E2E, Container IoC)
```

## Code Style & Architecture Conventions
- **Single Class per File:** Cada entidade, value object, aggregate, evento de domínio, DTO (Request/Response), caso de uso, interface/protocolo e adaptador de infraestrutura reside estritamente em seu próprio arquivo isolado. Arquivos `__init__.py` funcionam exclusivamente como facades.
- **Clean Architecture & Inversão de Dependências:** Domínio e Aplicação dependem apenas de abstrações (`Protocol` / `ABC`), isolando qualquer dependência de framework ou driver de terceiros.
- **Tratamento Funcional de Erros com `Result[T, E]`:** Casos de uso e operações de domínio retornam `Ok(value)` ou `Err(error)`, eliminando exceções não tratadas em regras de negócio.
- **Tipagem Estrita (Mypy Strict):** 100% do código tipado sem uso implícito de `Any`.
- **Validação Dinâmica de Esquemas:** Extração ontológica orientada por `pydantic.create_model` para validação determinística de nós e arestas.

## Boundaries
- **Always:**
  - Executar o gate oficial `make pre-commit` antes de commits.
  - Manter 1 classe por arquivo em todas as camadas.
  - Utilizar operações assíncronas (`async`/`await`) em qualquer chamada de I/O ou banco.
  - Executar operações síncronas bloqueantes em threadpool via `asyncio.to_thread`.
- **Ask first:**
  - Adição de dependências pesadas ou serviços adicionais no docker-compose.
  - Quebra de compatibilidade em eventos de domínio ou rotas públicas da API.
- **Never:**
  - Realizar bypass de tipagem estrita ou suprimir erros com `# type: ignore` sem justificativa formal.
  - Misturar múltiplos DTOs, entidades ou adaptadores no mesmo arquivo.
  - Incluir credenciais, segredos ou arquivos temporários no Git.

## Success Criteria & Capacidades Validadas
1. **Gerenciamento de Ontologias:** Criação, recuperação e listagem de templates de ontologia reutilizáveis (`OntologyTemplate`).
2. **Criação de Knowledge Base:** Inicialização com ontologia inline ou vinculada por `ontology_id` via Event Sourcing (`KnowledgeBaseCreatedEvent`).
3. **Storage Particionado & Parsing:** Upload assíncrono particionado (`data/storage/{kb_id}/{doc_id}`) e parsing local via MarkItDown.
4. **Saga Coreografada com 5 Eventos:** `DocumentAttachedEvent` ➔ `DocumentStoredEvent` ➔ `DocumentParsedToMarkdownEvent` ➔ `GraphExtractedFromDocumentEvent` ➔ `DocumentKnowledgeIndexedEvent`.
5. **Persistência Híbrida Real:**
   - Vetores: `PgVectorStoreAdapter` com similaridade de cosseno e isolamento por `kb_id`.
   - Grafos: `FalkorDbGraphStoreAdapter` com OpenCypher parametrizado contra injeção.
   - Eventos: `PostgresEventStore` com controle de versão otimista.
6. **Container IoC Configurável:** Alternância transparente entre infraestrutura real e in-memory via variáveis de ambiente.
7. **Qualidade Total:** 100% de testes automatizados passando e zero erros de linter ou tipagem.
