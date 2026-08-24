# SPEC-multimodal-ingestion-and-source-filtering: Pipeline Unificado Multimodal (Document, Image, Audio) & Filtros Temporais/Origem

## 1. Contexto e Motivação
O **Agentic Substrate** foi concebido como uma base de conhecimento agnóstica e de alto desempenho para múltiplos casos de uso, incluindo a fundação para sistemas de *Second Brain* e agentes autônomos. 

Originalmente, o pipeline de ingestão tratava principalmente arquivos de texto, PDFs e documentos de escritório (`.docx`, `.xlsx`, `.pptx`). Para viabilizar a captura sem fricção no dia a dia (notas mentais de voz, fotos de quadros, screenshots, gravações móveis e transcrições), o pipeline de ingestão é expandido de forma **polimórfica e modular**, convertendo qualquer artefato suportado em **Markdown estruturado de alta fidelidade** antes de entrar nas fases de chunking hierárquico, extração ontológica e indexação híbrida (FalkorDB + Postgres).

Além disso, para responder a consultas temporais em linguagem natural (*"O áudio que gravei semana passada sobre XPTO"*, *"Artigos que li no mês passado"*), a **temporalidade e a procedência** passam a ser cidadãos de primeira classe em todo o ciclo de vida: da ingestão à recuperação vetorial e por grafo.

---

## 2. Universo Fechado de Formatos & Classificação de Origem (`SourceType`)

O sistema classifica deterministicamente todo arquivo anexado em um de três tipos de origem (`SourceType`):

```
                                    ┌───────────────────────┐
                                    │    UPLOAD / INGRESS   │
                                    │ (MIME / FileExtension)│
                                    └───────────┬───────────┘
                                                │
                                                ▼
                        ┌───────────────────────────────────────────────┐
                        │      SourceTypeClassifier (Determinístico)    │
                        └───────┬───────────────┬───────────────┬───────┘
                                │               │               │
                 ┌──────────────┘               │               └──────────────┐
                 ▼                              ▼                              ▼
        ┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
        │ 📄 'document'   │            │ 🖼️ 'image'      │            │ 🎙️ 'audio'      │
        └────────┬────────┘            └────────┬────────┘            └────────┬────────┘
                 │                              │                              │
                 ▼                              ▼                              ▼
        ┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
        │ MarkItDown      │            │ OpenRouter VLM  │            │ OpenRouter      │
        │ + Fast-Path     │            │ (Qwen-2.5-VL)   │            │ whisper-large-v3│
        └────────┬────────┘            └────────┬────────┘            └────────┬────────┘
                 │                              │                              │
                 │                              │                              ▼
                 │                              │                     ┌─────────────────┐
                 │                              │                     │ Formatação      │
                 │                              │                     │ Markdown c/ ToC │
                 │                              │                     │ Temporal        │
                 │                              │                     └────────┬────────┘
                 │                              │                              │
                 └──────────────────────┬───────┴──────────────────────────────┘
                                        │
                                        ▼
                             Markdown Canônico Limpo
                                        │
                                        ▼
                      StructureTolerantMarkdownChunker
                                        │
                                        ▼
                      Parent/Child Chunks com Metadados
                      [source_type, ingested_at] ──► FalkorDB & Postgres
```

### 2.1. Matriz de Formatos e MimeTypes Suportados

| `SourceType` | Extensões Suportadas | MIME Types | Pipeline de Conversão para Markdown |
| :--- | :--- | :--- | :--- |
| **`document`** | `.md`, `.markdown`, `.txt`, `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.html`, `.htm`, `.json` | `text/markdown`, `text/plain`, `application/pdf`, `application/vnd.openxmlformats-officedocument.*`, `text/csv`, `text/html`, `application/json` | **`MarkItDown` + Fast-Path Nativo:** Converte estrutura hierárquica, tabelas e parágrafos diretamente em Markdown. PDFs com OCR ativado continuam usando o `ParallelVlmDocumentParser`. |
| **`image`** | `.png`, `.jpg`, `.jpeg`, `.webp`, `.heic`, `.heif` | `image/png`, `image/jpeg`, `image/webp`, `image/heic`, `image/heif` | **`VlmImageDocumentParser` (OCR Visual OpenRouter):** Normalização de HEIC/WebP para JPEG/PNG (via `pillow-heif` / `Pillow`) e transcrição direta via VLM (ex: `qwen/qwen-2.5-vl-72b-instruct` ou `google/gemini-2.0-flash-001`) gerando Markdown descritivo com tabelas e textos extraídos. |
| **`audio`** | `.mp3`, `.m4a`, `.ogg`, `.opus`, `.oga`, `.webm`, `.wav`, `.aac`, `.caf`, `.amr`, `.3gp` | `audio/mpeg`, `audio/mp4`, `audio/x-m4a`, `audio/ogg`, `audio/opus`, `audio/webm`, `audio/wav`, `audio/aac`, `audio/x-caf`, `audio/amr`, `audio/3gpp` | **`OpenRouterWhisperAudioDocumentParser` (Speech-to-Text):** Transcrição de áudio via OpenRouter (`openai/whisper-large-v3`) obtendo segmentos detalhados (`verbose_json`), com formatador determinístico em seções Markdown estruturadas por blocos temporais. |

---

## 3. Arquitetura de Temporalidade (End-to-End Time Pipeline)

### 3.1. Ingestão & Indexação Temporal
1. No momento do upload, o sistema anexa o timestamp Epoch UTC (`ingested_at: float`).
2. Todos os nós `ParentChunk` e `ChildChunk` recebem essa propriedade indexada no FalkorDB e no Postgres.
3. No FalkorDB: `CREATE INDEX FOR (p:ParentChunk) ON (p.ingested_at)`.

### 3.2. Normalização Temporal em Linguagem Natural (`QueryTemporalNormalizer`)
Para permitir que o usuário pergunte de forma humana sem precisar passar parâmetros de data manualmente na API:
* **Entrada:** `"O que o Roberto comentou sobre XPTO na semana passada?"` + `reference_time = 2026-08-20T15:30:00Z`
* **Processamento:** Componente de pré-processamento leve de query (via heurísticas + LLM estruturado Pydantic):
  * `cleaned_semantic_query`: `"O que o Roberto comentou sobre XPTO"`
  * `time_from`: `1786665600.0` (segunda-feira da semana passada, 00:00 UTC)
  * `time_to`: `1787270399.0` (domingo da semana passada, 23:59 UTC)
  * `inferred_source_types`: `["audio", "document"]` (se mencionado explicitamente, ou `None` se aberto).

### 3.3. Filtragem e Decaimento Temporal no Grafo
* **Filtro Estrito:** Quando a query define um intervalo explícito (`time_from` / `time_to`), a query Cypher filtra rigidamente os nós `ParentChunk`.
* **Filtro Suave / Temporal Boost (Opcional):** Quando o usuário busca por termos recentes sem intervalo fechado, chunks mais recentes recebem um multiplicador suave de relevância no `fused_score`.

---

## 4. Design da Formatação da Transcrição de Áudio (`AudioTranscriptionFormatter`)

O modelo `openai/whisper-large-v3` via OpenRouter retorna os segmentos temporais (`start`, `end`, `text`). Para garantir que o nosso `StructureTolerantMarkdownChunker` gere nós `ParentChunk` e `ChildChunk` de alta precisão sem alucinação, a transcrição é convertida deterministicamente pelo `AudioTranscriptionFormatter` em blocos de até 2 a 3 minutos ou por quebras de silêncio:

```markdown
# Transcrição de Áudio: {file_name}
*Data de Ingestão: {data_formatada}* | *Formato Original: {extensao}*

## [00:00 - 02:15]
Olá a todos. Nesta reunião vamos discutir o planejamento do trimestre e alinhar as entregas principais...

## [02:15 - 04:30]
O ponto principal levantado pelo time de arquitetura foi a separação dos parsers multimodais para suportar imagens e áudios...
```

---

## 5. Arquitetura e Contratos de Domínio

### 5.1. Novo Value Object: `DocumentSourceType`
```python
# src/modules/knowledge/domain/value_objects/document_source_type.py
from enum import Enum


class DocumentSourceType(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
```

### 5.2. Atualização em `DocumentAttachedEvent`
```python
# src/modules/knowledge/domain/events/document_attached_event.py
class DocumentAttachedEvent(DomainEvent):
    document_id: UUID
    file_name: str
    content_type: str
    storage_path: str
    source_type: DocumentSourceType
    ingested_at: float  # Epoch timestamp UTC determinístico
    enable_ocr: bool = False
    ocr_instructions: str | None = None
```

### 5.3. Propagação nos Chunks (`ParentChunk` e `ChildChunk`)
Os nós do grafo e registros de banco retêm deterministicamente a procedência e a data de ingestão:
* `ParentChunk.metadata["source_type"] = source_type.value`
* `ParentChunk.metadata["ingested_at"] = ingested_at`
* `ChildChunk.metadata["source_type"] = source_type.value`
* `ChildChunk.metadata["ingested_at"] = ingested_at`

---

## 6. Design dos Parsers Multimodais (Polimorfismo em Infraestrutura)

Para respeitar a regra inegociável de **Single Class per File**, os parsers são modularizados e orquestrados por uma fábrica / dispatcher composto:

```
src/modules/knowledge/infrastructure/adapters/
├── composite_document_parser.py                 # Orquestrador / Dispatcher principal (implementa IDocumentParser)
├── markitdown_document_parser.py                 # Parser nativo de documentos de texto/office/pdf
├── parallel_vlm_document_parser.py               # Parser paralelo com ToC para PDFs complexos
├── vlm_image_document_parser.py                  # Parser dedicado de imagens estáticas (PNG, JPG, HEIC, WebP)
├── openrouter_whisper_audio_document_parser.py   # Parser de áudios via OpenRouter Whisper
└── audio_transcription_formatter.py             # Formatador determinístico de segmentos para Markdown
```

### 6.1. `CompositeDocumentParser` (Dispatcher)
Implementa `IDocumentParser`. Ao receber `parse_to_markdown`, inspeciona o `content_type` ou a extensão do arquivo:
1. Se for `image/*` ou `.heic`/`.heif`: Delega para `VlmImageDocumentParser`.
2. Se for `audio/*` ou `.ogg`/`.opus`/`.m4a`/`.caf`/etc.: Delega para `OpenRouterWhisperAudioDocumentParser`.
3. Se for PDF com `enable_ocr=True`: Delega para `ParallelVlmDocumentParser`.
4. Caso contrário: Delega para `MarkItDownDocumentParser`.

### 6.2. `VlmImageDocumentParser`
* Converte mídias `.heic`/`.heif` usando `pillow_heif` para buffer JPEG/PNG padrão em memória.
* Envia imagem em Base64 para o modelo VLM configurado no OpenRouter (`qwen/qwen-2.5-vl-72b-instruct`).
* Formata a resposta como Markdown contendo cabeçalhos semânticos, tabelas detectadas e transcrição textual.

### 6.3. `OpenRouterWhisperAudioDocumentParser`
* Envia o áudio via `httpx.AsyncClient` com multipart form-data para o endpoint `/v1/audio/transcriptions` do OpenRouter usando `openai/whisper-large-v3` e solicitando `response_format="verbose_json"`.
* Passa a lista de segmentos temporais para o `AudioTranscriptionFormatter` gerar o Markdown estruturado final.

---

## 7. Suporte a Filtros em Busca Híbrida (`FalkorDB` + `Postgres`)

### 7.1. Contrato do Caso de Uso de Busca (`HybridSearchRequest`)
```python
class HybridSearchRequest(BaseModel):
    kb_id: UUID
    query: str
    top_k: int = 5
    candidate_k: int = 50
    time_from: float | None = None  # Epoch UTC mínimo
    time_to: float | None = None  # Epoch UTC máximo
    source_types: list[str] | None = None  # Filtro opcional: ["document", "audio", "image"]
```

### 7.2. Query Cypher Otimizada com Índices no FalkorDB
No `FalkorDbGraphStoreAdapter`:
* Criação de índices de propriedade:
  * `CREATE INDEX FOR (p:ParentChunk) ON (p.ingested_at)`
  * `CREATE INDEX FOR (p:ParentChunk) ON (p.source_type)`
* Cláusula de filtragem determinística na expansão de sementes e vizinhos:
  ```cypher
  CALL db.idx.vector.queryNodes('ChildChunk', 'embedding', $candidate_k, vecf32($query_vec))
  YIELD node AS child, score AS vec_score
  MATCH (p_seed:ParentChunk)-[:CONTAINS_CHILD]->(child)
  WHERE ($time_from IS NULL OR p_seed.ingested_at >= $time_from)
    AND ($time_to IS NULL OR p_seed.ingested_at <= $time_to)
    AND ($source_types IS NULL OR p_seed.source_type IN $source_types)
  WITH p_seed, max(1.0 - vec_score) AS seed_score
  ORDER BY seed_score DESC
  ...
  ```

---

## 8. Plano de Testes e Critérios de Aceite

### 8.1. Critérios de Sucesso
1. **Upload de Imagens:** Upload de arquivos `.png`, `.jpg`, `.webp` e `.heic` é aceito na API, classificado como `source_type="image"` e convertido em Markdown descritivo via OpenRouter VLM.
2. **Upload de Áudios:** Upload de arquivos `.mp3`, `.m4a`, `.ogg`, `.wav`, `.webm` é classificado como `source_type="audio"`, transcrito via OpenRouter `whisper-large-v3`, formatado com seções temporais em Markdown e inserido no grafo com chunks válidos.
3. **Persistência de Metadados e Temporalidade:** Todo nó `ParentChunk` e `ChildChunk` gravado no FalkorDB possui `ingested_at` (float epoch UTC) e `source_type` (string) populados.
4. **Filtros Temporais em Cypher:** A query de busca híbrida no FalkorDB filtra candidatos deterministicamente quando `time_from`/`time_to` e `source_types` são passados.
5. **Normalização de Queries Temporais:** O pipeline de consulta RAG consegue extrair janelas temporais de consultas em linguagem natural (*"na semana passada"*, *"nos últimos 3 dias"*) e aplicar os filtros na busca híbrida.
6. **Quality Gates:** 100% dos testes unitários e de integração passando, `mypy --strict` sem erros e `ruff` formatado.

---

## 9. Boundaries & Regras
- **Always:** Seguir rigorosamente a regra *Single Class per File* e tipagem estrita com `Result[T, E]`.
- **Ask First:** Antes de introduzir novas dependências pesadas no `pyproject.toml` (ex: `pillow-heif`).
- **Never:** Salvar credenciais ou quebrar retrocompatibilidade com documentos já ingeridos.
