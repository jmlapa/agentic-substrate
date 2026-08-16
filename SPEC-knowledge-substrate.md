# Spec: Knowledge Substrate (Marco 1: Kernel + Knowledge + API Gateway)

## Objective
Construir um substrato modular em Clean Architecture para desenvolvimento de sistemas agênticos, focado no gerenciamento de bases de conhecimento (Knowledge Bases) com GraphRAG. 
O sistema utiliza **Event Sourcing**, **Saga Coreografada** assíncrona, particionamento de storage por KB, extração estruturada de nós/arestas baseada em **ontologias dinâmicas em runtime** (usando Pydantic) e armazenamento híbrido (Grafos + Vetores).

## Tech Stack
- **Linguagem:** Python 3.12+
- **Gerenciador de Dependências & Ambiente:** `uv` / `poetry` / `pyproject.toml`
- **Framework Web:** FastAPI + Uvicorn (ASGI assíncrono)
- **Validação & Tipagem Dinâmica:** Pydantic v2
- **Event Sourcing & Persistence:** PostgreSQL (Event Store, Snapshots e pgvector) + Driver `asyncpg` / `SQLAlchemy Async`
- **Object Storage:** Compatível com S3 (MinIO localmente via `aioboto3` ou `minio-py`)
- **Graph Store:** Abstração no domínio com adaptadores (ex: FalkorDB/Neo4j ou Property Graph in Postgres)
- **Qualidade & Testes:** Pytest (pytest-asyncio), Ruff (linter/formatter), Mypy (type-checking estrito)

## Commands
```bash
# Instalação de dependências
uv sync # ou pip install -e ".[dev]"

# Executar suíte de testes com cobertura
pytest --cov=src -v

# Linter e Formatação
ruff check .
ruff format .

# Checagem de tipos estrita
mypy src

# Subir infraestrutura local (Postgres, MinIO, etc.)
docker compose -f docker/docker-compose.yml up -d

# Executar API Gateway localmente
uvicorn src.api_gateway.main:app --reload --port 8000
```

## Project Structure
```
agentic-substrate/
├── CAPABILITY-MAP.md
├── SPEC-knowledge-substrate.md
├── docker/
│   └── docker-compose.yml
├── pyproject.toml
├── src/
│   ├── kernel/                  # Primitivas puras de Domínio e Aplicação
│   │   ├── domain/              # Entity, ValueObject, AggregateRoot, DomainEvent, Result
│   │   ├── application/         # IEventBus, IEventStore, ILogger, IUseCase
│   │   └── infrastructure/      # EventStore in-memory/postgres, In-Memory EventBus
│   │
│   ├── modules/
│   │   └── knowledge/           # Módulo GraphRAG & Base de Conhecimento
│   │       ├── domain/          # KnowledgeBase, Document, OntologySchema, GraphNode, GraphEdge
│   │       ├── application/     # Sagas, Event Handlers, Use Cases (CreateKB, IngestDoc, Query)
│   │       │   ├── sagas/       # IngestionSagaCoordinator e handlers de steps
│   │       │   └── use_cases/   # Casos de uso de entrada e consulta
│   │       └── infrastructure/  # MinIOStorage, MarkdownParser, DynamicPydanticExtractor, VectorStore, GraphStore
│   │
│   └── api_gateway/             # Ponto de entrada HTTP
│       ├── controllers/         # Rotas REST assíncronas
│       ├── dependencies.py      # Injeção e Composição de Dependências (IoC)
│       └── main.py              # Aplicação FastAPI e middlewares
└── tests/
    ├── unit/                    # Testes de unidade puros (Domínio e Aplicação)
    └── integration/             # Testes de integração (Storage, Event Store, API)
```

## Code Style & Architecture Conventions
- **Single Class per File (Segregação Estrita de Arquivos):** Cada entidade, value object, aggregate, evento de domínio, DTO (Request/Response), caso de uso, interface/protocolo e adaptador de infraestrutura DEVE residir em seu próprio arquivo isolado. É expressamente proibido agrupar múltiplos casos de uso, DTOs ou entidades em mono-arquivos. Os arquivos `__init__.py` devem ser utilizados apenas para expor a API pública do pacote (facade).
- **Clean Architecture:** Camadas internas (`domain`) NUNCA dependem de camadas externas (`infrastructure`, `api_gateway`).
- **Interfaces por Protocolos:** Utilizar `typing.Protocol` ou `abc.ABC` para contratos de infraestrutura definidos no domínio/aplicação.
- **Tratamento de Falhas com `Result[T, E]`:** Métodos de domínio e casos de uso retornam estruturas explícitas `Result.ok(val)` ou `Result.err(error)` evitando exceções não controladas para regras de negócio.
- **Tipagem Forte em Runtime:** Ontologias de KBs geram classes dinâmicas `pydantic.create_model` para validação determinística de saídas de LLM.

## Boundaries
- **Always:**
  - Garantir que cada módulo tenha sua pasta e contratos isolados.
  - Manter o `kernel` sem nenhuma regra de negócio específica de módulos.
  - Criar testes unitários para toda regra de domínio e passos da Saga.
  - Validar tipos com `mypy` e conformidade com `ruff`.
- **Ask first:**
  - Adição de serviços externos adicionais além dos especificados (Postgres, MinIO, Vector/Graph).
  - Alterações no modelo ontológico base ou quebras de compatibilidade nos schemas de eventos.
- **Never:**
  - Fazer acoplamento direto entre submódulos sem passar por interfaces do `kernel` ou contratos públicos.
  - Gravar credenciais, API keys ou segredos em arquivos de configuração ou código.

## Success Criteria
1. Criação de Knowledge Bases com definição de Ontologias dinâmicas (Nós, Propriedades e Arestas permitidas).
2. Upload assíncrono particionado por KB em Object Storage.
3. Execução da Saga coreografada orientada a Event Sourcing:
   - `DocumentUploadedEvent` ➔ `DocumentStoredEvent` ➔ `DocumentParsedToMarkdownEvent` ➔ `GraphExtractedEvent` ➔ `KnowledgeIndexedEvent`.
4. Extrator dinâmico baseado em Pydantic validando tipagem estrita de nós e relacionamentos extraídos.
5. Endpoints REST da API funcionais com injeção de dependências desacoplada e 100% de testes unitários passando.
