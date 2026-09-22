# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0] - 2026-09-22

### Added
- **Google Drive Folder Data Source & Blue/Green Ingestion (Marco 1.25)**:
  - **Domínio e Casos de Uso (`src/modules/knowledge/`)**:
    - Entidade `DataSource` com ciclo de vida de status (`IDLE`, `SYNCING`, `FAILED`, `DISABLED`) e avanço de cursor delta.
    - Value Objects: `GoogleDriveFolderConfig` (validação alfanumérica estrita, `extra="forbid"`), `DiscoveredDocumentItem`, `DataSourceChangesBatch`, `DataSourceRun`.
    - Adaptador `GoogleDriveFolderConnector` integrando a Google Drive API v3 via Service Account do GCP.
    - Casos de Uso: `CreateDataSourceUseCase`, `ListDataSourcesUseCase`, `DeleteDataSourceUseCase`, `SyncDataSourceUseCase`, `ListDataSourceRunsUseCase`.
    - Repositórios Postgres e In-Memory: `PostgresDataSourceRepository` e `PostgresDataSourceRunRepository` (Migração `0007_data_sources_and_runs.py`).
  - **Blue/Green Document Swap & Ingestão Contínua**:
    - Ingestão em partição isolada (*Green*); substituição atômica no FalkorDB e storage apenas após 100% de sucesso na indexação ontológica e vetorial, eliminando downtime de busca e contradições factuais.
  - **Hardening de Segurança e Isolamento**:
    - Prevenção BOLA/IDOR com verificação explícita de `kb_id` nas rotas de deleção, sincronização e histórico de runs.
    - Proteção contra Drive Query Injection via regex restritiva `^(root|[a-zA-Z0-9_-]+)$`.
    - Defesa contra DoS com limite de tamanho de arquivo de 50MB (`max_file_size_bytes`) e higienização contra Path Traversal (`Path(item.name).name`).
  - **Interface Web no Frontend Console (`frontend/src/components/data-sources/`)**:
    - Aba dedicada **"Fontes de Dados / Google Drive"** na visualização da Knowledge Base (`KnowledgeBaseDetailPage.tsx`).
    - `CreateDataSourceModal`: Formulário com auto-extração de Folder ID a partir de links completos do navegador (`/folders/...` e `/shared-drives/...`), seletor de MIME types, baseline days e flag recursiva.
    - `DataSourceCard`: Card com badges de status em tempo real, último sync, intervalo e acionamento manual ("Sincronizar Agora").
    - `DataSourceRunsModal`: Auditoria completa de execuções com contadores de descobertos, indexados, falhas e accordion para inspecionar erros específicos por arquivo.
    - Hooks reativos (`useDataSources.ts`) com polling inteligente de 2.5s durante sincronizações ativas.
  - **Infraestrutura, VM Deploy & Documentação**:
    - Mapeamento de `GOOGLE_APPLICATION_CREDENTIALS` em `AppSettings` e injeção automática no `container.py`.
    - Montagem do volume `./credentials:/app/credentials:ro` no `docker-compose.yml` e automação no `deploy/vm/setup.sh`.
    - Guia detalhado de deploy no `README.md`, `SPEC-vm-all-in-one-deploy.md`, `SPEC-google-drive-folder-data-source.md` e ADR-0014.

## [0.9.0] - 2026-09-21

### Added
- **MCP Agent Connect Hub & Catálogo Dinâmico de Ferramentas (Marco 1.24)**:
  - **Introspecção O(1) de Ferramentas no Backend (`src/api_gateway/controllers/mcp_controller.py`)**:
    - Endpoint `GET /api/v1/mcp/info` inspeciona dinamicamente os provedores de ferramentas MCP (`IMcpToolProvider`) do servidor FastMCP sem exigir conexões SSE persistentes do navegador.
    - DTOs dedicados com Pydantic v2 seguindo estritamente a disciplina Single Class per File: `McpToolParameterDto`, `McpToolInfoDto` e `McpInfoResponseDto`.
    - Suíte de testes unitários em `tests/unit/api_gateway/test_mcp_controller.py`.
  - **Camada de Integração Frontend (`frontend/src/api/mcp-api.ts`, `frontend/src/hooks/useMcpInfo.ts`)**:
    - Cliente tipado e proxy `/mcp` configurado no `frontend/vite.config.ts`.
    - Hook TanStack React Query com polling inteligente a cada 10s e monitoramento de conectividade em tempo real.
  - **Componentes Modulares de Conexão MCP (`frontend/src/pages/mcp/components/`)**:
    - `McpHealthBanner`: Status visual de conectividade (Online/Offline), contagem em tempo real de ferramentas ativas e campo editável de Base URL com resolução dinâmica de portas (localhost:8000 vs origin de produção).
    - `McpCodeSnippet`: Bloco de código com destaque e cópia rápida em 1 clique com confirmação visual.
    - `McpToolsCatalog`: Catálogo interativo com visualização detalhada de parâmetros tipados, obrigatoriedade e categorização de ferramentas.
    - `McpClientSelectorTabs`: Suporte com sintaxes e comandos oficiais para 10 clientes e SDKs:
      1. Claude Code (CLI)
      2. Claude Desktop
      3. GitHub Copilot (VS Code Agent Mode)
      4. Antigravity CLI (DeepMind AGY)
      5. Cursor
      6. Gemini CLI
      7. OpenCode
      8. ChatGPT / OpenAI Codex
      9. Python MCP SDK
      10. Node.js / TypeScript MCP SDK
    - `McpBasicAuthPanel`: Suporte nativo à proteção por Caddy Basic Auth (`deploy/vm/rules/auth.caddy`), com cálculo reativo de credenciais Base64 (RFC 7617) e injeção automática de headers `Authorization` em todas as configurações dos agentes.
  - **Navegação & Roteamento (`frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`)**:
    - Nova rota `/mcp` mapeada para a página `McpConnectHubPage`.
    - Link de navegação no menu lateral com ícone de rede e badge indicativo.
  - **Documentação e Planejamento**:
    - Especificação técnica `SPEC-mcp-agent-connect-hub.md` e documento de pesquisa `docs/ideas/mcp-agent-connect-hub.md`.

## [0.8.1] - 2026-09-21

### Added
- **Regras Modulares no Caddy & Deploy Zero-Conflito em VM (Marco 1.23)**:
  - **Ponto de Extensão Dinâmico (`deploy/vm/Caddyfile`)**:
    - Adicionada diretiva `import /etc/caddy/rules/*.caddy` permitindo injeção de configurações específicas de ambiente (como `basic_auth`, whitelists de IP e headers customizados) sem alterar o `Caddyfile` rastreado.
  - **Isolamento de Ambiente e Diretório de Regras (`deploy/vm/rules/`)**:
    - Montagem do volume `./rules:/etc/caddy/rules:ro` no serviço `caddy` em `docker-compose.yml`.
    - Criação de `deploy/vm/rules/auth.caddy.example` com template documentado para geração de hash bcrypt via utilitário Caddy.
    - Criação de `deploy/vm/rules/README.md` com guia de boas práticas de extensão do proxy.
    - Garantia de criação idempotente do diretório `rules/` no `deploy/vm/setup.sh`.
  - **Isolamento no Controle de Versão (`.gitignore`)**:
    - Exclusão de `deploy/vm/rules/*.caddy` do controle de versão para impedir árvores de trabalho sujas (`dirty working tree`) na VM e permitir atualizações limpas com `git pull origin main`.
  - **Documentação de Acesso Direto por IP**:
    - Atualização do `deploy/vm/.env.example` documentando o uso de `DOMAIN_NAME=:80` para ambientes de staging sem domínio/TLS.
  - **Documentação Técnica e Arquitetural**:
    - Criação de `SPEC-modular-caddy-rules-and-vm-deployment.md` e registro da decisão em `docs/decisions/0013-modular-caddy-rules-and-zero-conflict-deployment.md`.

## [0.8.0] - 2026-09-18

### Added
- **Servidor Streamable HTTP/SSE Model Context Protocol (MCP - Marco 1.22)**:
  - **Servidor MCP Unificado na Borda (`src/api_gateway/mcp/`)**:
    - Servidor montado em `/mcp` no FastAPI (`/mcp/sse` para handshake SSE e `/mcp/messages` para mensagens JSON-RPC 2.0).
    - Integração nativa in-process com o `AppContainer` com resolução dinâmica de container ativo durante o lifespan da aplicação.
  - **Ferramentas Cognitivas e de Descoberta (`src/api_gateway/mcp/tools/`)**:
    - `KnowledgeQueryTool` (`knowledge_query`): Execução assíncrona de GraphRAG com síntese factual e evidências de grafo opcionais.
    - `KnowledgeListKbsTool` (`knowledge_list_kbs`): Listagem de bases de conhecimento cadastradas com métricas de documentos e status.
    - `KnowledgeSearchNotesTool` (`knowledge_search_notes`): Busca rápida por cabeçalhos e trechos sem custo de tokens LLM.
  - **Provedor Modular de Ferramentas (`src/api_gateway/mcp/providers/`)**:
    - Protocolo `IMcpToolProvider` e implementação `KnowledgeMcpToolProvider` seguindo estritamente a disciplina Single Class per File.
  - **Suporte a Streaming em Proxy Reverso (`deploy/vm/Caddyfile`)**:
    - Configuração de rota `/mcp/*` com desativação explícita de buffer (`flush_interval -1`) para entrega imediata de eventos SSE.
  - **Suíte de Testes Automatizados**:
    - Testes unitários com mocks em `tests/unit/api_gateway/mcp/`.
    - Teste de integração end-to-end com o cliente MCP oficial (`mcp.client.sse`) em `tests/integration/test_mcp_sse_server.py`.
  - **Documentação Arquitetural**:
    - Criação de `docs/decisions/0012-streamable-http-sse-mcp-server.md` e atualização da especificação técnica `SPEC-streamable-mcp-server.md`.

## [0.7.1] - 2026-09-16

### Removed
- **Descontinuação de `pydantic-ai` e Purga de Dependências**:
  - Remoção de `pydantic-ai>=2.31.0` do `pyproject.toml` e exclusão de 67 pacotes transitivos pesados não utilizados (`google-genai`, `opentelemetry-*`, `logfire`, etc.).
  - Remoção dos adaptadores legados de extração: `PydanticAiGraphExtractor`, `PydanticAiOpenRouterProviderFactory`, `ExistingEntityRegistry` e `IEntityRegistry`.
  - Remoção de parsers e chunkers obsoletos: `MarkItDownDocumentParser` (substituído por `ParallelVlmDocumentParser`), `MarkdownParentChildChunker` (substituído por `StructureTolerantMarkdownChunker`), `DeepSeekRagSynthesizer` e `GeminiRagSynthesizer` (substituídos por `OpenRouterRagSynthesizer`).
  - Remoção de scripts PoC descartáveis da pasta `scripts/` (`poc_hierarchical_json_toc.py`, `poc_sliding_window_ocr.py`, `poc_synthetic_toc_qwen.py`).
  - Limpeza de variáveis de ambiente fantasmas em `AppSettings`, `.env.example`, `deploy/vm/.env.example` e `docker/docker-compose.yml` (`GEMINI_MODEL_NAME`, `GEMINI_MAX_RPM`, `GEMINI_MAX_TPM`, `GEMINI_MAX_CONCURRENCY`, `GRAPH_EXTRACTOR_PROVIDER`, `OCR_TOC_BATCH_SIZE`, `OCR_DEFAULT_MARKDOWN_PROMPT`, `S3_*`, `STORAGE_TYPE`).

### Changed
- **Dependência Explícita do SDK OpenAI para OpenRouter**:
  - Adição direta de `openai>=1.40.0` no `pyproject.toml` para comunicação com a API OpenRouter via `DirectOpenRouterGraphExtractor` e `OpenRouterRagSynthesizer`.
- **Fiação do IoC Container (`Container`)**:
  - Configuração exclusiva do `DirectOpenRouterGraphExtractor` (com fallback determinístico local) e `OpenRouterRagSynthesizer`.
- **Frontend Pipeline Tracker**:
  - Atualização do indicador de status da etapa de extração de ontologia de `PydanticAI` para `OpenRouter`.

### Documentation
- **ADRs e Especificações Técnicas**:
  - Criação do `ADR-0011: Deprecation of PydanticAI, Legacy Parsers/Chunkers, and Environment Hardening`.
  - Atualização do `ADR-0003` (marcado como superado por ADR-0010 e ADR-0011).
  - Sincronização do `CAPABILITY-MAP.md`, `README.md`, `SPEC-pydantic-ai-graph-extractor-and-rate-limiter.md` e `SPEC-knowledge-chunking-and-embeddings.md`.

## [0.7.0] - 2026-09-15

### Added
- **Módulo de Deploy All-in-One em VM Única (`deploy/vm/` - Marco 1.21)**:
  - **Orquestração Docker Compose (`deploy/vm/docker-compose.yml`)**:
    - Coordenação dos 6 serviços fundamentais: Caddy 2, Frontend Console SPA (Nginx), API Gateway (FastAPI), PostgreSQL 16 (+ pgvector), Unified FalkorDB e Redis 7.
    - Isolamento rigoroso de portas: apenas portas `80` e `443` expostas no host; portas de banco de dados (`5432`, `6379`, `6380`) e API (`8000`) restritas à rede interna `substrate_net`.
    - Persistência contínua em disco de bloco SSD (`./data/...`) eliminando risco de perda de grafos, vetores e eventos.
  - **Edge Proxy Caddy 2 (`deploy/vm/Caddyfile`)**:
    - Emissão e renovação automática de certificados SSL/TLS via Let's Encrypt para domínio ou localhost.
    - Compressão nativa `zstd` e `gzip` para ativos estáticos.
    - Roteamento unificado de `/*` para o Frontend e `/api/*` e `/docs*` para a API Gateway com buffers desabilitados (`flush_interval -1`) para streaming SSE em tempo real, eliminando problemas de CORS.
  - **Script de Automação Idempotente (`deploy/vm/setup.sh`)**:
    - Script executável para VMs Debian/Ubuntu (AWS EC2, GCP Compute Engine, Hetzner, etc.).
    - Instalação automática de Docker Engine e Docker Compose v2 caso ausentes.
    - Suporte a injeção automatizada de `.env` via Terraform/cloud-init ou geração assistida com senha segura randômica para o PostgreSQL.
    - Execução automática de migrações (`alembic upgrade head`) e healthchecks em cascata.
  - **Suíte de Testes Automatizados de Configuração (`tests/unit/test_deploy_vm_configuration.py`)**:
    - Testes unitários com Pytest validando topologia de rede, ausência de portas de banco no host, rotas do Caddyfile, cobertura de variáveis e sintaxe do script de setup.
  - **Documentação & Especificação Formal**:
    - Criação de `SPEC-vm-all-in-one-deploy.md`, artefato conceitual em `docs/ideas/staging-cloud-deployment.md` e guia de deploy de 1 comando no `README.md`.

## [0.6.2] - 2026-08-31

### Fixed
- **Retentativas Automáticas com Backoff Exponencial no Pipeline VLM & LLM**:
  - `ParallelVlmDocumentParser`: Implementação de retentativas automáticas (3 tentativas com backoff `1s`, `2s`, `4s`) por página de OCR para resiliência a oscilações transitórias de rede, timeouts e HTTP 429 (Rate Limit), eliminando descarte silencioso de páginas e garantindo preservação atômica em `PageCheckpointStorage`.
  - `QwenSyntheticTocExtractor`: Retentativas automáticas com backoff por lote na geração do Sumário Sintético (ToC).
  - `DirectOpenRouterGraphExtractor`: Retentativas com backoff exponencial antes de ativação de fallback heurístico.
- **Normalização e Exposição de Diagnósticos de Erro na Saga e Read Model**:
  - `PostgresKnowledgeBaseRepository` & `KnowledgeController`: Padronização do payload de erro nos DTOs (`step`, `message` e `error_message`), corrigindo incompatibilidade de chave que ocultava os detalhes de erro no frontend.
  - `PipelineStatusTracker` & `KnowledgeBaseDetailPage`: Destaque visual imediato da etapa específica em falha (alerta vermelho), preservação do status de etapas precedentes concluídas (verde) e exibição de diagnósticos de erro acionáveis na interface.
- **Controle de Concorrência na Extração de Grafos de Documentos Extensos**:
  - `DocumentIngestionSagaCoordinator`: Bounding de concorrência com `asyncio.Semaphore(15)` no processamento concorrente de centenas de `ParentChunks` em documentos longos (ex: PDFs com 400+ páginas), prevenindo saturação de sockets e do event loop.

## [0.6.1] - 2026-08-24

### Added
- **Configuração Centralizada de Provedor OpenRouter (`OpenRouterProviderDefaults`)**:
  - Centralização de políticas de roteamento com priorização estrita de `sort: "throughput"`, `allow_fallbacks: True` e supressão de raciocínio não-estruturado (`reasoning: {effort: "none", exclude: True}`).
  - Métodos utilitários para injeção de `extra_body` em clientes OpenAI/AsyncOpenAI e cabeçalhos governados (`HTTP-Referer` e `X-Title`).

### Changed
- **Padronização Global de Throughput em Chamadas OpenRouter**:
  - `DirectOpenRouterGraphExtractor`: Injeção de `extra_body` com throughput routing na extração direta de grafos.
  - `ParallelVlmDocumentParser` & `QwenSyntheticTocExtractor`: Migração das diretivas inline para `OpenRouterProviderDefaults`.
  - `OpenRouterRagSynthesizer` & `VlmImageDocumentParser`: Headers e payload padronizados via `OpenRouterProviderDefaults`.
  - `OpenRouterClientFactory` & `PydanticAiOpenRouterProviderFactory`: Reutilização centralizada dos cabeçalhos canônicos e atalho `get_throughput_extra_body()`.
- **Modelo Padrão de Visão/OCR (VLM)**:
  - Definido `qwen/qwen3-vl-32b-instruct` como modelo padrão de OCR em `AppSettings`, adaptadores e templates de ambiente (`.env.example`), oferecendo maior qualidade de extração e menor custo por milhão de tokens na OpenRouter.

## [0.6.0] - 2026-08-24

### Added
- **Extrator Ontológico Direto & Suíte de Avaliação de Modelos (Marco 1.20 / ADR-0010)**:
  - **`DirectOpenRouterGraphExtractor`**:
    - Implementação de alta velocidade de `IGraphExtractor` com chamadas diretas de completion via OpenRouter (`response_format: {"type": "json_object"}`).
    - Eliminação do overhead de frameworks agênticos (`PydanticAI`) e injeção de prompts inchados.
    - Filtro ativo de integridade referencial: descarte de arestas órfãs antes da persistência no grafo.
    - Normalização polimórfica resiliente via validadores Pydantic v2.
  - **Suíte de Benchmark & Avaliação (`scripts/eval_graph_extractors.py`)**:
    - Cenários de teste automatizados em 3 níveis de complexidade (Baixa, Média e Alta).
    - Medição empírica de latência (ms), integridade referencial de arestas (%) e aderência ao schema (%).
  - **Documentação de Arquitetura & Decisões**:
    - Criação do [ADR-0010: Lean 7B/8B Structured Extractor](file:///Users/insider/personal/agentic-substrate/docs/decisions/0010-lean-7b-direct-openrouter-structured-extractor.md).
    - Criação de [SPEC-lean-7b-direct-openrouter-structured-extractor.md](file:///Users/insider/personal/agentic-substrate/SPEC-lean-7b-direct-openrouter-structured-extractor.md).
    - Registro do estudo comparativo em [docs/ideas/lean-7b-ontology-extractor.md](file:///Users/insider/personal/agentic-substrate/docs/ideas/lean-7b-ontology-extractor.md).

### Changed
- **Eleição do Modelo Padrão de Extração**:
  - `OPENROUTER_GRAPH_MODEL_NAME` alterado de `google/gemma-4-26b-a4b-it` para `meta-llama/llama-3.1-8b-instruct`.
  - Injeção do `DirectOpenRouterGraphExtractor` no `AppContainer` (`src/api_gateway/container.py`).
  - Redução de latência de extração por chunk em até 30x (de ~15s para ~0.5s).

## [0.5.1] - 2026-08-24

### Added
- **Normalizador de Continuidade em Markdown & Deduplicação de Cabeçalhos no VLM OCR (Marco 1.19)**:
  - **Deduplicação Determinística de Cabeçalhos Adjacentes (`_dedup_adjacent_headers`)**:
    - Detecção e eliminação de cabeçalhos markdown repetidos entre transições de página (insensível a maiúsculas/minúsculas e espaçamentos).
    - Preservação estrita de cabeçalhos legítimos não-adjacentes e conteúdos separados por parágrafos.
  - **Orquestração de Limpeza e Normalização (`_normalize_markdown`)**:
    - Remoção automática de marcadores de página (`<!-- PAGE N -->`) e blocos de erro (`<!-- [Erro no OCR...] -->`).
    - Colapso de quebras de linha consecutivas redundantes (`\n{3,}` $\rightarrow$ `\n\n`) e corte de espaços residuais nas bordas.
  - **Instruções de Continuidade Estrutural no System Prompt do OCR**:
    - *Continuidade de Hierarquia*: Não repetição de títulos de seções já ativas no topo da página subsequente.
    - *Continuidade de Texto*: Continuação direta de parágrafos entre páginas sem inserção de quebras artificiais.
    - *Tabelas Inter-Página*: Re-emissão dos cabeçalhos de colunas GFM para tabelas fragmentadas entre páginas.

### Changed
- **Pipeline de Saída do `ParallelVlmDocumentParser`**:
  - Aplicação de `_normalize_markdown` nos dois pontos de saída (`fast-path` de cache com 100% de acerto e fluxo normal de OCR paralelo), garantindo geração de documentos markdown contínuos e sem marcadores artificiais.

## [0.5.0] - 2026-08-23

### Added
- **Pipeline de Ingestion Multimodal & Filtros Semânticos/Temporais no GraphRAG (Marco 1.17)**:
  - **Classificador e Value Object de Origem (`DocumentSourceType`)**:
    - Classificação determinística estrita em 3 origens universais (`document`, `image`, `audio`).
    - Suporte nativo a extensões e MIME types para documentos (`.md`, `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.html`, `.json`), imagens (`.png`, `.jpg`, `.jpeg`, `.webp`, `.heic`, `.heif`) e áudios (`.mp3`, `.m4a`, `.ogg`, `.opus`, `.webm`, `.wav`, `.aac`, `.caf`, `.amr`, `.3gp`).
  - **Parsers Multimodais Especializados**:
    - `OpenRouterWhisperAudioDocumentParser`: Transcrição de áudio assíncrona multipart via OpenRouter Whisper Large v3 (`openai/whisper-large-v3`) com segmentação temporal e formatação Markdown estruturada (`## [MM:SS - MM:SS]`).
    - `AudioTranscriptionFormatter`: Agrupamento resiliente de timestamps e falas com tolerância a pausas de oradores.
    - `VlmImageDocumentParser`: Conversão em memória (JPEG/PNG/WebP/HEIC) via Pillow e extração OCR descritiva e estruturada via modelos VLM (`qwen/qwen-2.5-vl-72b-instruct` / `qwen/qwen3-vl-32b-instruct`).
    - `CompositeDocumentParser`: Dispatcher polimórfico de `IDocumentParser` para roteamento determinístico baseado na extensão/MIME type.
  - **Metadados Temporais e de Proveniência em Todo o Grafo**:
    - Gravação atômica de `source_type` e `ingested_at` nos eventos de domínio (`DocumentAttachedEvent`), agregados (`KnowledgeBaseAggregate`) e nós Cypher (`ParentChunk`, `ChildChunk`).
    - Criação de índices de range no FalkorDB: `CREATE INDEX FOR (p:ParentChunk) ON (p.source_type)` e `ON (p.ingested_at)`.
  - **Filtros de Proveniência e Janela Temporal na Busca Híbrida & API**:
    - Parâmetros `source_types: list[str] | None`, `time_from: float | None` e `time_to: float | None` propagados do DTO HTTP (`POST /api/v1/knowledge/bases/{kb_id}/query`) até a query Cypher híbrida no FalkorDB e no motor `InMemoryGraphStore`.
    - Enriquecimento do `retrieval_trace` e dos resultados retornados (`HybridSearchResult`) com os metadados de proveniência e tempo.

## [0.4.0] - 2026-08-19


### Added
- **Exclusão em Cascata de Knowledge Bases, Documentos e Ontologias**:
  - **Exclusão Atômica de Documentos (`DELETE /api/v1/knowledge/bases/{kb_id}/documents/{doc_id}`)**:
    - Remoção física dos arquivos em disco (`raw`, `processed`, `checkpoints`).
    - Exclusão do subgrafo Cypher no FalkorDB via `DETACH DELETE (d:Document), (p:ParentChunk), (c:ChildChunk)`.
    - Emissão de `DocumentDeletedEvent` no aggregate e projeção no repositório relacional.
  - **Exclusão Completa de Knowledge Base (`DELETE /api/v1/knowledge/bases/{kb_id}`)**:
    - Limpeza de diretórios e partições no Local Storage.
    - Exclusão do grafo FalkorDB dedicado (`kb_{kb_id}`).
    - Emissão de `KnowledgeBaseDeletedEvent` e remoção do repositório PostgreSQL/In-Memory.
  - **Exclusão de Ontologias com Proteção de Integridade Referencial (`DELETE /api/v1/ontologies/{ontology_id}`)**:
    - Verificação de dependências (`count_usages`); retorno HTTP 409 Conflict se estiver vinculada a Knowledge Bases ativas.
  - **Integração no Frontend**:
    - React Query mutations em `useKnowledgeBases.ts` e `useOntologies.ts`.
    - Botões de lixeira e modais de confirmação em `KnowledgeBasesListPage`, `KnowledgeBaseDetailPage`, `OntologiesListPage` e `OntologyDetailPage`.
    - Melhorias na seleção e validação de múltiplos tipos de arquivo em `DocumentUploadModal.tsx`.

## [0.3.9] - 2026-08-19

### Added
- **Natural Parent Deduplication, 50-Candidate Oversampling & Bounded Multiplicative Decay in GraphRAG (ADR-0009)**:
  - **Eliminação do Afunilamento Precoce de Sementes (*Seed Pool Starvation*)**:
    - Remoção do `LIMIT` intermediário na seleção de sementes vetoriais na consulta Cypher do `FalkorDbGraphStoreAdapter`.
    - Deduplicação natural de todos os `ParentChunk`s derivados dos 50 melhores filhos do índice HNSW.
    - Expansão de vizinhos ontológicos ampliada de 2 para até 5 vizinhos mais conectados (`[0..5]`) por semente.
    - Aplicação estrita do `LIMIT $top_k` apenas após o cálculo do `fused_score` e ordenação global, garantindo invariância e máxima relevância na posição #1 independentemente do `top_k` solicitado.
  - **Reranking com *Bounded Multiplicative Graph Decay***:
    - Substituição da fórmula aditiva vulnerável a nós hub/índices por decaimento proporcional relativo: sementes diretas preservam seu score vetorial de cosseno ($1.0 - distance$) e vizinhos entram com decaimento de salto ($0.70\times$) e bônus proporcional limitado ($\le 25\%$):
      `fused_score = base_score * (1.0 + (min(shared_entities, 5) * 0.05))`.
    - Eliminação completa de inflação por páginas de índice remissivo e glossários em documentos legais extensos.
  - **Oversampling Mínimo Expandido**:
    - `candidate_k` no `QueryKnowledgeUseCase` padronizado como $\max(top\_k \times 4, 50)$ (mínimo de 50 `ChildChunk`s).
  - **Busca Semântica Assimétrica (`embed_query`)**:
    - `QueryKnowledgeUseCase` agora invoca `IEmbeddingService.embed_query` com a instrução oficial do Gemini 2 (`task: search result | query: ...`) para máxima precisão pergunta-resposta.
  - **Otimização de Throughput & Supressão de Raciocínio no OpenRouter**:
    - Configuração de `provider: {"sort": "throughput", "allow_fallbacks": True}` no `OpenRouterRagSynthesizer`, roteando dinamicamente para os clusters de inferência com maior vazão (~95 tokens/s via Parasail).
    - Desativação explícita de tokens de raciocínio com `reasoning: {"effort": "none", "exclude": True}`, reduzindo o tempo de síntese em mais de 60%.
  - **Adoção do Qwen3 VL 32B Dense no OCR Multimodal e Synthetic ToC**:
    - Substituição do modelo padrão de visão de `qwen/qwen3-vl-30b-a3b-instruct` para `qwen/qwen3-vl-32b-instruct`.
    - Ganho de ~30% em velocidade de OCR por página (~65 tokens/s vs ~40 tokens/s) com redução de 20% no custo por token.
    - Injeção de roteamento `provider: {"sort": "throughput"}` e supressão de reasoning em `ParallelVlmDocumentParser` e `QwenSyntheticTocExtractor`.
  - **Grounding Estrito e Ausência de Dados nos Sintetizadores RAG**:
    - Reforço das instruções de sistema em `OpenRouterRagSynthesizer` e `GeminiRagSynthesizer` proibindo expressamente o uso de conhecimento prévio e forçando a declaração padronizada de ausência de informações caso o contexto recuperado seja insuficiente ou irrelevante.
  - **Testes de Invariância Top-1 e Documentação**:
    - Suíte de testes atualizada comprovando que `top_k=1` avalia todo o pool de sementes e retorna o mesmo nó campeão que `top_k=3` ou `top_k=5`.
    - Criação do `docs/decisions/0009-bounded-multiplicative-graph-decay-and-natural-deduplication.md`.

## [0.3.8] - 2026-08-19

### Added
- **Optimized GraphRAG Retrieval, Candidate Fusion & 32k Dynamic Token Budgeting (Marco 1.15)**:
  - **FalkorDB Cypher Candidate Expansion (Fórmula $K + 2K$)**:
    - Expansão atômica de até 2 nós vizinhos por semente vetorial via entidades compartilhadas (`[0..2]`), gerando universo de 9 candidatos para `top_k=3`.
    - Fusão de scores no Cypher (`fused_score = base_score + shared_entities * 0.10`) com cálculo de similaridade por distância de cosseno (`1.0 - vec_score`).
    - Navegação linear entre chunks pais com arestas `[:NEXT]` criadas em batch (`prev_chunk_id` e `next_chunk_id`).
  - **Dynamic Token Budgeting (50 a 32k Tokens)**:
    - Truncamento proporcional inteligente no `QueryKnowledgeUseCase` garantindo inclusão obrigatória do Chunk #1 e descarte de micro-fragmentos (<50 tokens).
    - Teto configurável ampliado para até **32.000 tokens** (`max_tokens_budget`).
  - **Defesa Contra Indirect Prompt Injection**:
    - Encapsulamento estrito das evidências e triplas recuperadas em tags XML `<evidence>` estruturadas.
  - **Padronização Oficial no Google Gemma 4**:
    - `OpenRouterRagSynthesizer` e `PydanticAiGraphExtractor` padronizados para utilizar **Google Gemma 4 (`google/gemma-4-26b-a4b-it`)** via OpenRouter como modelo padrão de síntese fact-dense e extração ontológica.
    - Criação dos ADRs 0007 e 0008 e atualização completa de todas as especificações técnicas.

## [0.3.7] - 2026-08-18


### Added
- **Rich Markdown Renderer for RAG Playground & Evidence Inspector (Marco 1.18)**:
  - **Componente `MarkdownRenderer`**:
    - Suporte a GitHub Flavored Markdown (GFM) completo via `react-markdown` e `remark-gfm`.
    - Mapeamento estilizado de títulos `h1`-`h4`, parágrafos, listas numeradas e com marcadores, blockquotes estilizados e links com segurança (`target="_blank"`).
  - **Componente `CodeBlock`**:
    - Bloco de código com tema escuro elegante, badge de identificação de linguagem (ex: `PYTHON`, `SQL`, `CYPHER`) e botão de cópia rápida com feedback tátil de 2s.
  - **Tabelas GFM Ricas**:
    - Mapeamento de tabelas responsivas com scroll horizontal, linhas zebradas e cabeçalhos em negrito.
  - **Integração no Playground RAG**:
    - Substituição da `div` estática com `whitespace-pre-wrap` em `AnswerView.tsx` e snippets de chunks em `EvidenceInspector.tsx` pela renderização rica do `MarkdownRenderer`.

## [0.3.6] - 2026-08-18

### Added
- **Real-Time Telemetry Precision, Continuous Pipeline Transitions & Frontend Polish (Marco 1.17)**:
  - **Limpeza de Mensagens de OCR e Contador Agregado**:
    - Substituição da mensagem do OCR interpolada por `page_num` pela contagem acumulada `"Processando OCR: {cur}/{total_pages} páginas concluídas"`, eliminando oscilações de números fora de ordem causadas pelo término concorrente de workers.
  - **Cálculo de Percentual com Teto Estrito (99% Guard)**:
    - Garantia matemática de que o percentual de conclusão nunca exiba $100\%$ enquanto existirem itens pendentes na etapa ($cur < tot$), eliminando arredondamentos precoces no frontend.
  - **Transições de Telemetria Instantâneas e Contínuas**:
    - Emissão de `DocumentProgressUpdatedEvent` imediato nos inícios das etapas de `CHUNKING`, `GRAPH_EXTRACTION` e `EMBEDDINGS`, proporcionando feedback visual contínuo ao usuário enquanto os lotes são preparados.
  - **Sincronização Explícita do Read Model no Projector**:
    - Atualização dos handlers `handle_document_parsed`, `handle_document_chunked` e `handle_document_indexed` no `KnowledgeBaseProjector` para sincronizar e limpar mensagens de etapas anteriores no PostgreSQL.
  - **Polimento Visual do Frontend (`PipelineStatusTracker`)**:
    - Renderização limpa com ícone animado de spinner, truncamento defensivo de textos longos e badge condicional `{pct}% ({cur}/{tot})` com transições suaves de layout.

## [0.3.5] - 2026-08-18

### Added
- **Resilient ToC Checkpoints, Monotonic Telemetry & Thread-Safe Fast-Path OCR (Marco 1.16)**:
  - **`TocCheckpointStorage`**:
    - Persistência atômica granular de lotes do Synthetic ToC (`toc_cache/{doc_id}/batch_{batch_num:04d}.json`) contendo itens e o estado de passagem (`TocBatchState`).
    - Persistência do ToC consolidado (`toc_cache/{doc_id}/toc.json`) eliminando reprocessamento de ToC em caso de reinicialização da saga a custo **$0.00**.
  - **Fast-Path OCR Cache Hit**:
    - Se todas as páginas do documento já estiverem presentes no `PageCheckpointStorage`, o `ParallelVlmDocumentParser` pula a etapa de ToC integralmente e monta o Markdown consolidado diretamente do disco em milissegundos sem chamadas à LLM.
  - **Fila de Workers e Telemetria Monotônica (`asyncio.Queue`)**:
    - Refatoração do OCR concorrente para usar fila de workers com uso de RAM constante $O(\text{concurrency})$ em vez de $O(N)$ corrotinas.
    - Substituição do envio de índice estático por contador atômico de páginas concluídas (`completed_count`), eliminando a oscilação visual de progresso no frontend ($x \rightarrow x-4$).
    - Contador atômico `completed_parents` na extração de grafos no coordenador da Saga.
  - **Thread-Safety no Renderizador C-PDFium**:
    - Mutex de thread (`threading.Lock`) no `PdfPageRenderer` garantindo isolamento seguro em picos de concorrência multithread.
  - **Guarda Monotônica no Projector**:
    - Query SQL no `KnowledgeBaseProjector` com cláusula `GREATEST` para impedir regressão de percentual em caso de desordem de pacotes de rede.

## [0.3.4] - 2026-08-18

### Added
- **Resilient Saga Reprocessing, Redis Job Queues & Zero-Token-Waste Checkpoints (Marco 1.15)**:
  - **Checkpoints Atômicos em Disco com Custo Zero ($0.00)**:
    - `PageCheckpointStorage`: Salva cada página transcrita por OCR em `ocr_cache/{doc_id}/page_{page_num:04d}.md`. Retomadas e reprocessamentos reutilizam instantaneamente páginas já processadas sem nenhuma chamada à API de VLM.
    - `ParentGraphCheckpointStorage`: Salva grafos ontológicos Pydantic extraídos por Parent Chunk em `graph_cache/{doc_id}/parent_{parent_id}.json`. Retomadas carregam o grafo do disco sem chamadas adicionais de LLM.
    - Cache estrutural de Chunks em `chunks/{doc_id}_chunks.json` evitando re-chunking redundante.
  - **Filas de Jobs Assíncronas (`IJobQueue`)**:
    - Implementações `InMemoryJobQueue` e `RedisJobQueue` (baseada em listas atômicas `LPUSH` / `BLPOP`).
    - Value Objects imutáveis `JobTask`, `PageOcrJobPayload` e `ParentGraphJobPayload`.
  - **Telemetria Granular de Progresso e CQRS**:
    - Novo evento de domínio `DocumentProgressUpdatedEvent` emitindo percentual, página/chunk atual, total e mensagens contextuais.
    - Migração Alembic `0007_add_document_progress_telemetry.py` e atualização do `KnowledgeBaseProjector` para persistência em tempo real nas colunas `progress_step`, `progress_current`, `progress_total`, `progress_percentage` e `progress_message`.
  - **Endpoint e Caso de Uso de Reprocessamento**:
    - `ReprocessDocumentUseCase` e endpoint `POST /api/v1/knowledge/bases/{kb_id}/documents/{doc_id}/reprocess` para retomar ingestões interrompidas com total segurança.
  - **Frontend Real-Time Progress & Retry**:
    - Barra de progresso dinâmica em tempo real no `PipelineStatusTracker.tsx` com indicação de progresso e badges informativos.
    - Botão **"Retomar Ingestão (Zero Tokens)"** no card de documentos em `KnowledgeBaseDetailPage.tsx`.
  - **Micro-batches de Embeddings**:
    - Fatiamento de chunks filhos em micro-lotes de 50 embeddings por requisição, prevenindo estouro de payload HTTP e rate limits.

## [0.3.3] - 2026-08-18

### Added
- **Stateful Synthetic ToC & Resilient Parallel VLM OCR (`ParallelVlmDocumentParser`, `QwenSyntheticTocExtractor`, `PdfPageRenderer`)**:
  - **Passo 1 (Synthetic ToC)**: Extração da árvore hierárquica completa (`#`, `##`, `###`, `####`) mesmo para documentos sem sumário/índice através de fatiamento em lotes encadeados de 20-25 páginas em baixa resolução (1.0x / ~72 DPI) com passagem de estado ativo (`TocBatchState`).
  - **Passo 2 (Parallel Transcription)**: Transcrição simultânea de páginas em alta resolução (2.0x / ~200 DPI) com controle estrito de concorrência (`asyncio.Semaphore(ocr_max_concurrency)`), injeção determinística de hierarquia por página e resiliência a 429 com exponential backoff.
  - **Value Objects & Entidades de Domínio**: `HierarchicalTocItem`, `TocBatchState`, `SyntheticDocumentToc` e protocolo `ISyntheticTocExtractor`.
  - **Renderizador Dual-Scale**: `PdfPageRenderer` assíncrono com `pypdfium2` gerando JPEGs em memória em escalas 1.0x (ToC) e 2.0x (OCR).

## [0.3.2] - 2026-08-18

### Added
- **DeepSeek-V4-Flash Fact-Dense RAG Synthesizer (`DeepSeekRagSynthesizer`)**:
  - Novo adaptador de síntese RAG consumindo a API do OpenRouter (`deepseek/deepseek-v4-flash`) com temperatura determinística 0.1 e headers de governança.
  - Prompt estrito para Fact-Dense Markdown eliminando introduções/conclusões prolixas e exigindo citações diretas de nós e chunks (`[^chunk:<uuid>]`, `[^entidade:<tipo>:<nome>]`).
- **Arquitetura Dual-Mode de Consulta (`mode: "synthesis" | "retrieve"`)**:
  - Parâmetro `mode` em `QueryKnowledgeRequest` e `QueryKnowledgeDTO`.
  - Fast-Path `< 30ms` no `QueryKnowledgeUseCase` quando `mode == "retrieve"`, retornando imediatamente subgrafos e evidências para consumo por Tools de Agentes sem custo de LLM.
- **Frontend Query Playground Updates (`QueryPlaygroundView.tsx` & `AnswerView.tsx`)**:
  - Seletor interativo de modo de execução (`Síntese Fact-Dense (DeepSeek v4)` vs `Apenas Recuperação (Raw Fast-Path)`).
  - Atualização visual e tipográfica destacando o modelo DeepSeek-V4-Flash e proveniência estrita.

## [0.3.1] - 2026-08-18

### Added
- **CQRS Consolidated Read Model & Event-Driven Projections (`KnowledgeBaseProjector`)**:
  - Projector assíncrono escutando os 8 eventos de domínio do ciclo de vida da KB e sincronizando de forma idempotente as tabelas relacionais `knowledge_bases` e `attached_documents`.
  - Migration Alembic `0006_expand_attached_documents_read_model.py` expandindo a tabela de leitura com opções de OCR, contadores de chunks pai/filho, nós/arestas no FalkorDB e diagnósticos de erro.
  - Rotina de sincronização e backfill idempotente durante o bootstrap (`lifespan`) da API Gateway.
- **Repositório de Leitura O(1) com JOIN Ontológico (`PostgresKnowledgeBaseRepository`)**:
  - Consultas `get_by_id` e `list_all` executam `LEFT JOIN ontology_templates` para retornar o schema ontológico completo e métricas de documentos em tempo constante, sem necessidade de replay de eventos em requisições de leitura.
- **Frontend Pipeline Tracker & Card Ontológico**:
  - Correção do índice de conclusão no `PipelineStatusTracker.tsx`, exibindo checkmarks verdes em todas as etapas quando o status atinge `INDEXED`.
  - Card dedicado de **Ontologia Vinculada (Schema do Grafo)** na tela de detalhes da Knowledge Base (`KnowledgeBaseDetailPage.tsx`), com badges de entidades e relações.

## [0.3.0] - 2026-08-18

### Added
- **Configurable Multimodal OCR & OpenRouter Integration (`MarkItDownDocumentParser` & `OpenRouterClientFactory`)**:
  - **Fast-path Zero-Cost Default**: Plaintext and text-layer documents execute natively on CPU with zero LLM API calls and sub-second parsing speed.
  - **Multimodal Visual Analysis via OpenRouter**: Opt-in toggle to route image-heavy, diagrammatic, and scanned documents to `qwen/qwen3-vl-30b-a3b-instruct` (or configured VLM) through OpenRouter.
  - **Custom Markdown Structure Instructions (*Prompt Injection*)**: Upload request accepts custom formatting guidelines (e.g. strict GFM tables, mathematical preservation, standardized image annotations `> [Figura X: ...]`).
- **PydanticAI OpenRouter Responses Provider (`PydanticAiOpenRouterProviderFactory` & `PydanticAiGraphExtractor`)**:
  - Fábrica de modelos PydanticAI configurando `OpenAIResponsesModel` e `OpenAIProvider` com cliente `AsyncOpenAI` customizado.
  - Headers institucionais de governança (`HTTP-Referer`, `X-Title`) e controle deslizante de taxa de requisições via `RateLimitedAsyncTransport`.
  - Suporte ao modelo `deepseek/deepseek-v4-flash` para extração de grafos com alta precisão e baixo custo.
  - Fallback gracioso automático para extração determinística em cenários de indisponibilidade de rede ou ambientes de teste.
- **Backend API & Event Sourcing Updates**:
  - `POST /api/v1/knowledge/bases/{kb_id}/documents` accepts `enable_ocr: bool` and `ocr_instructions: str` via multipart form data.
  - `DocumentAttachedEvent` and `KnowledgeBaseAggregate` persist OCR preferences in event history.
  - `DocumentIngestionSagaCoordinator` propagates document OCR options to the parser step.
- **Frontend Console UI Enhancements**:
  - Added visual toggle in `DocumentUploadModal.tsx` for multimodal OCR with real-time fast-path zero-cost badge.
  - Added expandable textarea for optional Markdown structure instructions.
  - Updated API client and React Query hooks to transmit upload options seamlessly.

## [0.2.1] - 2026-08-17

### Added
- **Frontend Console SPA (`/frontend`)**:
  - Modern, responsive SPA built with **React 18.3.1 + Vite 5.4 + TypeScript 5.5 + Tailwind CSS 3.4** and TanStack React Query v5.
  - **Ontologies Hub**: Visual form to create and inspect domain schemas (entities, properties, relationships) and export JSON schemas.
  - **Knowledge Bases Hub**: Provisioning of KBs with ontology dropdown selector and inline creation modal.
  - **Document Ingestion & Live Pipeline Tracker**: Multi-file dropzone (PDF, TXT, MD, DOCX, JSON) with live visual Saga stage tracking (`Upload` ➔ `Parsing` ➔ `Chunking` ➔ `Grafo LLM` ➔ `Indexado`) and smart polling with auto-stop.
  - **RAG Query Playground**: Interactive query interface providing synthesized LLM answers via Gemini Flash-Lite paired with deep evidence inspection (retrieved chunks, relevance scores, and FalkorDB subgraphs/entities).
- **Backend RAG Synthesis & Listing Endpoints**:
  - `GET /api/v1/knowledge/bases`: Endpoint to list all Knowledge Bases with document metrics.
  - `POST /api/v1/knowledge/bases/{kb_id}/query`: Enriched with `ILlmSynthesisService` protocol (`GeminiRagSynthesizer` / `InMemoryRagSynthesizer`) generating grounded Markdown answers with factual citations.
- **Production Containerization**:
  - Multi-stage Dockerfile (`node:20-alpine` build + `nginx:1.27-alpine` runtime, image size < 25MB).
  - Added `frontend` service on port 3000 to `docker/docker-compose.yml` with SPA fallback and API reverse proxy.

## [0.2.0] - 2026-08-17

### Added
- **PydanticAI v2 Dynamic Graph Extractor (`PydanticAiGraphExtractor`)**:
  - Dynamically builds Pydantic models from user-defined `OntologySchema` at runtime.
  - Generates structured, strongly-typed JSON outputs using Google Gemini (`gemini-3.5-flash-lite`).
- **Transport-Level Rate Limiter (`RateLimitedAsyncTransport`)**:
  - Intercepts all outgoing HTTP transport requests with `AsyncTokenBucketLimiter`.
  - Non-blocking 60-second sliding window managing 300 RPM and 1.000.000 TPM with zero lock contention.
  - Automatic exponential backoff with full jitter for HTTP 429 (`ResourceExhausted`) responses.
- **Cumulative Canonical Entity Registry (`ExistingEntityRegistry`)**:
  - Caches and injects previously extracted entities per Knowledge Base into LLM extraction prompts to enforce entity ID reuse and eliminate cross-chunk duplication.
- **Universal Structure-Tolerant Markdown Chunker (`StructureTolerantMarkdownChunker`)**:
  - Uses `AtomicBlockLexer` to preserve tables, lists, and code blocks intact.
  - Emits contextual breadcrumb trails for Parent Chunks (~1.200 tokens) and overlapping Child Chunks (~200 tokens + 30 overlap).
- **High-Fidelity PDF Document Parsing (`MarkItDownDocumentParser`)**:
  - Added `markitdown[all]` support for robust PDF parsing with `pdfminer.six` and `pdfplumber`.
- **Parallelized Ingestion Saga Execution**:
  - Refactored `DocumentIngestionSagaCoordinator` with `asyncio.gather` for concurrent Parent Chunk processing bounded by `max_concurrency=15`.
- **Universal Brazilian Legal Ontology (`OntologiaJuridicaBrasileira`)**:
  - Modeled after LC 95/1998 with 7 core node types and 11 relationship types.
- **CLI Utility Scripts**:
  - `scripts/ingest_document.py`: Multi-format document ingestion pipeline CLI.
  - `scripts/register_legal_ontology.py`: Legal ontology registration CLI.
- **Architecture Decision Records (ADRs)**:
  - `ADR-0001: Hexagonal Event-Sourced Architecture with Single Class Per File`
  - `ADR-0002: Unified FalkorDB Hybrid GraphRAG Engine`
  - `ADR-0003: PydanticAI v2 Graph Extraction, Rate Limiting and Cumulative Canonization`
  - `ADR-0004: Universal Structure-Tolerant Markdown Chunker`
- **Real-World Document Benchmark**:
  - Successfully ingested and indexed the entire Brazilian Federal Constitution (CF/88, 437 pages, 1.34M characters, 293 Parent Chunks, 2.052 Child Chunks) into FalkorDB with verified sub-10ms hybrid search responses.

## [0.1.0] - 2026-08-16

### Added
- Unified FalkorDB Hybrid GraphRAG architecture with single-graph per Knowledge Base housing both structural document nodes (`:Document`, `:ParentChunk`, `:ChildChunk`) and ontological entity nodes (`:Entity`).
- Native FalkorDB HNSW vector index initialization (`ensure_vector_index`) on `(:ChildChunk.embedding)`.
- Structural document ingestion (`store_structural_document`) and parent-level conceptual mentions linking (`store_parent_mentions`) with `[:MENTIONS]` edges.
- Unified single-query OpenCypher hybrid search (`query_hybrid`) utilizing `db.idx.vector.queryNodes` with parent context ascension and connected entity expansion.
- Value objects `HybridSearchResult` and `StructuralGraphDocument` in `knowledge` domain.
- Centralized Settings and Secrets Management module (`AppSettings`) powered by `pydantic-settings` and `SecretStr`.
- Asynchronous database migration framework using Alembic and `asyncpg` (`make migrate`).
- Modular clean architecture with `kernel`, `knowledge`, and `api_gateway`.
- `kernel` domain primitives: `Entity`, `ValueObject`, `AggregateRoot`, `DomainEvent`, `DomainError`, and `Result[T, E]`.
- `kernel` application contracts: `UseCase`, `EventBus`, `EventStore`, and `Logger`.
- `kernel` infrastructure: `PostgresEventStore` with optimistic concurrency control and transactional locks.
- `knowledge` domain: `KnowledgeBase`, `Document`, `OntologyTemplate`, `OntologySchema`, `GraphNode`, `GraphEdge`.
- Dynamic ontology definitions with runtime Pydantic v2 validation (`DynamicOntologyModelBuilder`).
- Choreographed Event-Driven Ingestion Saga (`DocumentIngestionSagaCoordinator`) with Event Sourcing.
- `LocalFileSystemStorageAdapter` for partitioned asynchronous object storage with path traversal protection.
- `api_gateway` FastAPI REST endpoints for Ontology Templates, Knowledge Bases, Document Ingestion, and Knowledge Querying.
- Dependency injection container (`AppContainer`) supporting dynamic environment-based infrastructure selection.

### Removed
- Removed legacy `IVectorStore` interface and `PgVectorStoreAdapter` following unification of vector and graph queries directly in FalkorDB.
- Added Alembic migration `0004_drop_legacy_vector_tables.py` to drop redundant PostgreSQL tables `document_chunks` and `node_embeddings`.
- Unused dependencies `aioboto3` and `sqlalchemy` in favor of direct native `asyncpg` connection pooling.

### Verified
- Strict Mypy compliance (`strict = true`), 100% Ruff linting/formatting pass, and automated test coverage (93%+).
