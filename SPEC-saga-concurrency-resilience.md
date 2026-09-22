# SPEC-saga-concurrency-resilience: Resiliência de Concorrência na Saga de Ingestão (Deferred Atomic Commit & Optimistic Retry)

## 1. Contexto e Motivação

Durante a ingestão concorrente de múltiplos documentos pertencentes à mesma Knowledge Base (por exemplo, sincronização de 4 arquivos `.docx` via Google Drive), o pipeline de ingestão falhou silenciosamente para a maioria dos arquivos.

### Causa Raiz Diagnosticada
- **Monólito de Concorrência no Aggregate Root:** Todos os documentos de uma KB compartilham o mesmo `KnowledgeBaseAggregate` no Event Store PostgreSQL.
- **Janela de Retenção Excessiva (40s - 60s):** Na etapa `handle_document_chunked`, a saga carrega a instância do agregado na memória no início da execução (`_load_aggregate`) e a retém durante todo o processamento assíncrono (cálculo de embeddings vetoriais e 13 chamadas LLM ao OpenRouter).
- **Colisão de Versão Otimista:** Enquanto o documento A aguarda as respostas da LLM, o documento B (menor) conclui e persiste seus eventos, elevando o `event_version` do agregado no PostgreSQL de `v=27` para `v=35`.
- **Rejeição no Postgres:** Quando o documento A conclui a LLM e tenta persistir o evento `GraphExtractedFromDocumentEvent`, o PostgreSQL rejeita a gravação com `DomainError("Concurrency conflict: expected version 28, got 35")`.
- **Falha em Cascata no Tratamento de Erro:** O bloco `except Exception` tenta gravar a falha (`mark_processing_failed`) reutilizando a mesma instância de `kb` em memória com versão defasada, gerando um segundo conflito consecutivo e abortando a corrotina sem persistir nem o sucesso nem a falha.
- **Sintoma no Front-end:** O documento congela no estado `status="CHUNKED"` com a etapa "Grafo LLM" mostrando 100% e ícone de loading eterno.

---

## 2. Objetivos e Critérios de Sucesso

### 2.1 Objetivos Centrais
1. **Eliminar a Janela de Colisão Temporal:** Reduzir o tempo de retenção do `KnowledgeBaseAggregate` de dezenas de segundos (~40.000ms) para milissegundos (~5ms) através do padrão **Deferred Atomic Commit**.
2. **Mutex em Memória por Knowledge Base (`asyncio.Lock`):** Serializar estritamente a fase de recarga-mutação-gravação do agregado por `kb_id`, permitindo que o processamento pesado de I/O (LLM, embeddings, FalkorDB) continue 100% paralelo.
3. **Resiliência a Conflitos Concorrentes com Retry Loop Exponencial:** Capturar qualquer `DomainError` de conflito de versão e realizar até 5 tentativas imediatas (recarregando o agregado atualizado do banco e reaplicando a mutação em memória).
4. **Tratamento de Exceções Confiável (Zero Documentos Presos):** Garantir que qualquer falha real de negócio ou infraestrutura sempre consiga persistir `mark_processing_failed` com o erro registrado na projeção PostgreSQL, eliminando estados órfãos no front-end.
5. **Recuperação e Reprocessamento de Documentos Travados:** Permitir que o caso de uso `ReprocessDocumentUseCase` retome documentos presos em qualquer etapa não-terminal (`CHUNKED`, `PARSED`, `FAILED`), aproveitando 100% dos checkpoints já gravados em disco sem gastar tokens.

---

## 3. Tech Stack

- **Linguagem:** Python 3.12+ com Mypy em modo estrito (`strict = true`).
- **Frameworks:** FastAPI, asyncio nativo.
- **Armazenamento:** PostgreSQL (Event Store e Projeções CQRS via Asyncpg), FalkorDB (Grafo Semântico e Vetorial), Local File System Storage.
- **LLM & Embeddings:** OpenRouter Client Factory, Gemini Embedding 2.
- **Testes:** Pytest, pytest-asyncio.

---

## 4. Commands

- **Build / Verificação Pré-commit:**
  ```bash
  make pre-commit
  ```
- **Execução dos Testes da Saga:**
  ```bash
  poetry run pytest tests/modules/knowledge/application/test_document_ingestion_saga_concurrency.py -v
  ```
- **Lint e Formatação:**
  ```bash
  poetry run ruff check .
  poetry run ruff format --check .
  ```
- **Verificação Estrita de Tipos:**
  ```bash
  poetry run mypy src/
  ```

---

## 5. Project Structure

```
src/
└── modules/
    └── knowledge/
        └── application/
            ├── sagas/
            │   └── document_ingestion_saga_coordinator.py   # Implementação com Deferred Commit e Mutex
            └── use_cases/
                └── reprocess_document/
                    ├── reprocess_document_use_case.py       # Ajuste para suportar retomada em CHUNKED
                    ├── reprocess_document_request.py
                    └── reprocess_document_response.py
tests/
└── modules/
    └── knowledge/
        └── application/
            └── test_document_ingestion_saga_concurrency.py  # Teste de concorrência com múltiplos docs simultâneos
```

---

## 6. Code Style e Padrão de Implementação

### 6.1 Padrão "Deferred Atomic Commit with Retry"

```python
from collections import defaultdict
import asyncio
import random
from typing import Callable, TypeVar
from uuid import UUID

from src.kernel.domain.domain_error import DomainError
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)

T = TypeVar("T")

class DocumentIngestionSagaCoordinator:
    def __init__(self, ...) -> None:
        ...
        self._kb_locks: dict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def _execute_atomic_aggregate_mutation(
        self,
        kb_id: UUID,
        mutate_fn: Callable[[KnowledgeBaseAggregate], None],
        max_retries: int = 5,
    ) -> KnowledgeBaseAggregate:
        """Executa a mutação no agregado sob lock por KB com retry exponencial em caso de conflito."""
        lock = self._kb_locks[kb_id]
        async with lock:
            last_err: Exception | None = None
            for attempt in range(max_retries):
                try:
                    kb = await self._load_aggregate(kb_id)
                    mutate_fn(kb)
                    await self._save_aggregate(kb)
                    return kb
                except DomainError as err:
                    if "Concurrency conflict" in str(err):
                        last_err = err
                        backoff = (0.02 * (2**attempt)) + random.uniform(0.01, 0.03)
                        await asyncio.sleep(backoff)
                        continue
                    raise
                except Exception as err:
                    last_err = err
                    raise
            if last_err:
                raise last_err
            raise RuntimeError("Falha inesperada na mutação atômica do agregado")
```

---

## 7. Testing Strategy

1. **Teste de Concorrência de Ingestão:**
   - Simular 5 documentos associados à mesma `KnowledgeBaseAggregate` executando simultaneamente tarefas com durações variadas.
   - Assert: Todos os 5 documentos completam com sucesso, sem nenhuma exceção `Concurrency conflict` e com status final consistente.
2. **Teste de Tolerância a Falhas e Registro de Erro:**
   - Simular erro na etapa de extração e verificar que `mark_processing_failed` é persistido com sucesso mesmo sob concorrência de outros documentos.
3. **Teste de Reprocessamento Resiliente:**
   - Disparar `reprocess_document` para documento travado em `CHUNKED` e validar transição imediata para `INDEXED` consumindo o cache do disco.

---

## 8. Boundaries

### Always Do
- Liberar operações de rede (LLM, embeddings, parsing, FalkorDB) para execução paralela assíncrona **fora** de qualquer lock.
- Adquirir o lock da KB exclusivamente no momento de recarregar, mutar e salvar o agregado no Postgres.
- Executar `make pre-commit` e manter zero erros no Mypy strict e Ruff.
- Cumprir a regra *Single Class per File* (`AGENTS.md`).

### Ask First
- Alterar schemas de tabelas no PostgreSQL ou assinaturas de eventos de domínio públicos.
- Mudar regras de negócio do `KnowledgeBaseAggregate`.

### Never Do
- Segurar o agregado `KnowledgeBaseAggregate` em memória enquanto aguarda chamadas assíncronas I/O demoradas.
- Silenciar exceções no Event Store ou ignorar conflitos de concorrência.
- Deletar arquivos de checkpoints em disco (`graph_cache/`, `chunks/`, `ocr_cache/`).

---

## 9. Success Criteria

1. **Pipeline Completo:** O documento `4483722f-34fd-439e-89fd-c2417a48b8b4` (e os outros 2 travados) concluem o pipeline e atingem o status `INDEXED` com nós e arestas no FalkorDB.
2. **Zero Concurrency Collisions:** Ingestão de múltiplos documentos simultâneos não gera mais exceções não tratadas `Concurrency conflict: expected version X, got Y`.
3. **Resiliência Comprovada:** Teste automatizado de concorrência com 5 documentos em paralelo passa com 100% de sucesso.
4. **Gates Verificados:** `make pre-commit` executado com 100% dos testes passando e cobertura mantida.
