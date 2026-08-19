# Spec: Configurable OCR & Optimized Visual Ingestion Pipeline

## Objective
Prover um pipeline de ingestão de documentos híbrido, de alta velocidade e custo-otimizado com **MarkItDown**, integrando:
1. **OCR Multimodal Opcional (Opt-in pelo Frontend):** Documentos puramente textuais utilizam o parser nativo em C/Python sem invocar chamadas de LLM (custo zero e tempo de execução quase instantâneo).
2. **Processamento Visual Acelerado via OpenRouter / Qwen3-VL:** Quando o OCR é habilitado para documentos com diagramas, gráficos ou tabelas complexas, o sistema delega para o modelo multimodal `qwen/qwen3-vl-32b-instruct` (ou configurado) via OpenRouter com concorrência assíncrona e priorização por throughput.
3. **Diretrizes Customizadas de Estrutura Markdown (*Prompt Injection* no MarkItDown):** O usuário pode fornecer instruções personalizadas no momento do upload sobre como organizar o Markdown resultante (ex: preservação de fórmulas LaTeX, extração de tabelas em GFM, anotações padronizadas de imagens `> [Figura X: ...]`).

---

## Tech Stack
- **Backend Core:** Python 3.12, FastAPI, Pydantic v2, Pydantic Settings
- **Parsing & Multimodal:** `markitdown[all]`, `openai` (apontando para OpenRouter), `asyncio`
- **Frontend:** React 18, TypeScript, Tailwind CSS, Vite, Lucide Icons
- **Event Sourcing & Hexagonal Architecture:** Domain Events, Aggregates, Result[T, E] Pattern

---

## Commands
- **Lint & Format:** `make lint` / `ruff check .` & `ruff format --check .`
- **Type Checking:** `make typecheck` / `mypy .`
- **Tests & Coverage:** `make test` / `pytest tests/unit/modules/knowledge/ -v --cov`
- **Pre-Commit Gate:** `make pre-commit`
- **Frontend Dev:** `cd frontend && npm run dev`
- **Frontend Build & Check:** `cd frontend && npm run build`

---

## Project Structure & Touched Modules

```
src/
├── kernel/
│   └── infrastructure/
│       └── app_settings.py                      # Novas configurações: OPENROUTER_API_KEY, OCR_VISION_MODEL, OCR_MAX_CONCURRENCY
├── modules/
│   └── knowledge/
│       ├── domain/
│       │   ├── events/
│       │   │   └── document_attached_event.py   # Adição de enable_ocr e ocr_instructions
│       │   ├── interfaces/
│       │   │   └── i_document_parser.py         # Assinatura com suporte a opções de OCR e prompt
│       │   └── aggregates/
│       │       └── knowledge_base_aggregate.py  # Persistência das preferências de OCR por documento
│       ├── application/
│       │   ├── use_cases/
│       │   │   └── attach_and_store_document/   # Request/Response atualizados com enable_ocr e prompt
│       │   └── sagas/
│       │       └── document_ingestion_saga_coordinator.py # Passa opções de OCR do agregado para o parser
│       └── infrastructure/
│           └── adapters/
│               ├── markitdown_document_parser.py # Suporte a OpenRouter Client, custom prompt e fallback nativo
│               └── openrouter_client_factory.py  # Fábrica do cliente OpenAI compatível com OpenRouter
src/api_gateway/
├── controllers/
│   └── knowledge_controller.py                  # Endpoint /documents aceita enable_ocr e ocr_instructions via Form
└── dtos/
    └── upload_document_dto.py                   # DTO para validação e documentação Swagger
frontend/
├── src/
│   ├── api/
│   │   ├── types.ts                             # Tipagem de requisição atualizada
│   │   └── knowledge-api.ts                     # Envio de enable_ocr e ocr_instructions no FormData
│   └── pages/
│       └── ingestion/
│           └── DocumentUploadModal.tsx          # Switch/Toggle visual para OCR e textarea para instruções
```

---

## Code Style & Architecture Conventions

### 1. Assinatura do `IDocumentParser`
```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class IDocumentParser(Protocol):
    async def parse_to_markdown(
        self,
        raw_bytes: bytes,
        file_name: str,
        content_type: str,
        enable_ocr: bool = False,
        ocr_instructions: str | None = None,
    ) -> str: ...
```

### 2. Adaptação do `MarkItDownDocumentParser` com Fast-Path e OpenRouter
```python
class MarkItDownDocumentParser(IDocumentParser):
    def __init__(
        self,
        openrouter_client: Any | None = None,
        vision_model: str = "qwen/qwen3-vl-30b-a3b-instruct",
        default_instructions: str = "Transcribe document preserving tables, headings, and describe images in markdown.",
    ) -> None:
        self._client = openrouter_client
        self._vision_model = vision_model
        self._default_instructions = default_instructions

    def _get_markitdown_instance(self, enable_ocr: bool, instructions: str | None) -> MarkItDown:
        if not enable_ocr or not self._client:
            return MarkItDown()  # Fast-path nativo (custo zero)
        return MarkItDown(
            llm_client=self._client,
            llm_model=self._vision_model,
            llm_prompt=instructions or self._default_instructions,
        )
```

---

## Testing Strategy
1. **Unit Tests (`tests/unit/modules/knowledge/`):**
   - Testar `MarkItDownDocumentParser` com `enable_ocr=False` (verifica que nenhuma chamada HTTP ao LLM ocorre).
   - Testar `MarkItDownDocumentParser` com `enable_ocr=True` e `ocr_instructions` personalizadas (mock do cliente OpenRouter).
   - Testar `AttachAndStoreDocumentUseCase` garantindo que os campos `enable_ocr` e `ocr_instructions` sejam emitidos no `DocumentAttachedEvent`.
   - Testar `DocumentIngestionSagaCoordinator` repassando as flags para o parser.
2. **Integration Tests (`tests/integration/api_gateway/`):**
   - Testar `POST /api/v1/knowledge/bases/{kb_id}/documents` passando multipart form com `enable_ocr=true` e `ocr_instructions="Formatar tabelas em GFM"`.
3. **Frontend Validation:**
   - Testar renderização do toggle no `DocumentUploadModal` e verificação de envio correto do payload no `FormData`.

---

## Boundaries
- **Always:**
  - Garantir a regra *Single Class per File* para todos os novos DTOs, factories e adaptadores.
  - Manter 100% de tipagem estrita sem `Any` implícito (`strict = true` no mypy).
  - Preservar retrocompatibilidade: uploads sem o campo `enable_ocr` assumem `False` como padrão seguro (custo zero).
- **Ask first:**
  - Alterações de banco de dados ou migrações do Alembic.
  - Alterações no algoritmo de chunking hierárquico existente.
- **Never:**
  - Hardcodear chaves de API ou segredos no código.
  - Invocar o LLM de visão quando `enable_ocr=False` ou para arquivos puramente textuais (`.txt`, `.md`, `.json`, `.csv`).

---

## Success Criteria
- [ ] Upload de arquivos puramente textuais (.txt, .md, .csv) ou PDFs com `enable_ocr=false` é processado em < 1 segundo sem chamadas ao OpenRouter.
- [ ] Upload com `enable_ocr=true` utiliza o cliente OpenRouter com o modelo `qwen/qwen3-vl-30b-a3b-instruct` e o prompt customizado de formatação Markdown.
- [ ] No Frontend, o modal de upload disponibiliza o toggle de OCR com aviso de custo/tempo e campo opcional de instruções de formatação Markdown.
- [ ] Todos os gates de qualidade passam (`make pre-commit`: Ruff, Mypy Strict, 100% dos testes unitários/integração).
