# Implementation Plan: Configurable OCR & Optimized Visual Ingestion Pipeline

## Overview
Implementar o suporte a OCR multimodal configurável e acelerado no pipeline de ingestão de documentos com **MarkItDown**, permitindo:
1. **Fast-path nativo (custo zero e tempo quase instantâneo)** para documentos puramente textuais ou quando OCR não for selecionado.
2. **Processamento visual multimodal via OpenRouter (`Qwen3-VL-30B-A3B-Instruct`)** quando o usuário ativar a análise visual pelo frontend.
3. **Injeção de instruções personalizadas de formatação Markdown** enviadas pelo usuário no momento do upload.
4. **Interface no Frontend Console** com toggle intuitivo e campo de instruções de estrutura Markdown.

---

## Architecture Decisions
1. **Single Class per File & Hexagonal Architecture:**
   - `OpenRouterClientFactory` em `src/modules/knowledge/infrastructure/adapters/openrouter_client_factory.py`.
   - `IDocumentParser` atualizado com parâmetros nomeados opcionais em `src/modules/knowledge/domain/interfaces/i_document_parser.py`.
   - `MarkItDownDocumentParser` com chaveamento dinâmico entre o parser nativo leve e o wrapper VLM com `llm_client`, `llm_model` e `llm_prompt`.
2. **Event Sourcing & Agregados:**
   - `DocumentAttachedEvent` transporta `enable_ocr: bool` e `ocr_instructions: str | None`.
   - `KnowledgeBaseAggregate` persiste essas configurações no dicionário de documentos para que a saga assíncrona (`DocumentIngestionSagaCoordinator`) as forneça ao parser durante o step `PARSE_MARKDOWN`.
3. **Compatibilidade e Segurança de Tipos:**
   - Modo estrito no Mypy (`strict = true`).
   - Default de `enable_ocr` como `False` para manter retrocompatibilidade e garantir economia de tokens por padrão.
4. **Settings & Secrets:**
   - `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OCR_VISION_MODEL_NAME`, `OCR_MAX_CONCURRENCY` gerenciados no `AppSettings`.

---

## Task List

### Phase 1: Settings, Secrets & OpenRouter Client
- [ ] **Task 1: Settings & Environment Configuration**
  - Atualizar `AppSettings` em `src/kernel/infrastructure/app_settings.py`, `.env.example` e `.env` com configurações do OpenRouter e OCR.
- [ ] **Task 2: Implementar `OpenRouterClientFactory`**
  - Criar fábrica do cliente OpenAI configurado para o OpenRouter em `src/modules/knowledge/infrastructure/adapters/openrouter_client_factory.py`.

### Phase 2: Domain Interfaces & Aggregate Updates
- [ ] **Task 3: Atualizar `IDocumentParser` e `DocumentAttachedEvent`**
  - Adicionar `enable_ocr` e `ocr_instructions` na interface de parser e no evento de domínio.
- [ ] **Task 4: Atualizar `KnowledgeBaseAggregate`**
  - Persistir as flags de OCR no estado do aggregate root no momento do attach.

### Phase 3: Application Layer & MarkItDown Adapter
- [ ] **Task 5: Refatorar `MarkItDownDocumentParser`**
  - Suportar modo rápido nativo (sem LLM) e modo OCR com OpenRouter e prompt customizado.
- [ ] **Task 6: Atualizar Use Case e Saga Coordinator**
  - Atualizar `AttachAndStoreDocumentRequest`/`UseCase` e `DocumentIngestionSagaCoordinator` para repassar as opções de OCR.

### Phase 4: API Gateway & Dependency Injection
- [ ] **Task 7: Atualizar Endpoint de Upload no `KnowledgeController` e Container**
  - Receber `enable_ocr` e `ocr_instructions` via multipart `Form` e instanciar parser configurado no `AppContainer`.

### Phase 5: Frontend Console UI
- [ ] **Task 8: Atualizar Tipos e Client API no Frontend**
  - Atualizar `frontend/src/api/types.ts` e `frontend/src/api/knowledge-api.ts` para enviar os novos campos no `FormData`.
- [ ] **Task 9: Atualizar Modal de Upload (`DocumentUploadModal.tsx`)**
  - Adicionar switch de OCR, tooltip explicativo e campo de instruções de Markdown.

### Phase 6: Automated Tests & Pre-Commit Gate
- [ ] **Task 10: Testes Unitários e de Integração**
  - Testar parsing com e sem OCR, use case, saga e controller.
- [ ] **Task 11: Execução dos Gates Oficiais (`make pre-commit`, `npm run build`)**
  - Validar linters, tipagem estrita, testes com cobertura e build do frontend.

---

## Risks and Mitigations
| Risco | Impacto | Mitigação |
|---|---|---|
| Chave do OpenRouter ausente no ambiente | Baixo | Se `enable_ocr=True` for solicitado mas nenhuma chave de API estiver configurada, fallback automático para parsing nativo com log de aviso ou erro descritivo. |
| Documentos grandes com imagens pesadas | Médio | Concorrência assíncrona controlada por semáforo e timeouts bem definidos no cliente HTTP. |
| Quebra de retrocompatibilidade em uploads existentes | Baixo | `enable_ocr` possui valor padrão `False`. |
