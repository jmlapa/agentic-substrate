# Resilient Data Source Sync & Ingestion Queue

## Problem Statement
Como poderíamos transformar a sincronização de fontes de dados de um fluxo síncrono e frágil em uma esteira assíncrona orientada a filas leves, imune a colisões de I/O, com visibilidade clara de falhas e reprocessamento sob demanda na interface?

---

## Recommended Direction: Arquitetura Híbrida (Async Native + Task Queue com DLQ)

Adotar uma arquitetura em 3 camadas que resolve simultaneamente o gargalo de rede/thread-safety, a previsibilidade de execução em background e a experiência do usuário:

```
[UI Gateway] ──(POST /sync)──► [SyncDataSourceUseCase] (Descoberta Rápida ~200ms)
                                         │
                                         ▼ (Enfileira Jobs)
                               [Redis Task Queue / Stream]
                                         │
                                         ▼ (Concorrência controlada: N workers)
                            [Download & Ingestion Worker]
                                         │
                             ┌───────────┴───────────┐
                             │                       │
                     (Sucesso: 200 OK)       (Falha transitória)
                             │                       │
                             ▼                       ▼
                    [AttachDocument]         [Retry Backoff: 3x]
                             │                       │
                             ▼               (Esgotou retries)
                    [Document Saga]                  │
                                                     ▼
                                            [DLQ / Failure Summary]
                                                     │
                                                     ▼
                                            [UI: Botão "Tentar Novamente"]
```

### 1. Client HTTP Assíncrono Nativo (`httpx.AsyncClient`)
- Substituir o wrapper bloqueante `google-api-python-client` / `httplib2` por um cliente assíncrono enxuto em `httpx` consumindo diretamente os endpoints REST da API v3 do Google Drive (`/files/{id}?alt=media` e `/files/{id}/export`).
- Autenticação gerida via Service Account Bearer Token com refresh automático.
- Eliminação total de `asyncio.to_thread` em downloads e multiplexação segura de sockets SSL sem corrupção de camada de transporte (`record layer failure`).

### 2. Desacoplamento via Fila Leve de Tarefas (Redis + DLQ)
- O caso de uso `SyncDataSourceUseCase` apenas consulta a API para descobrir o delta de mudanças (`fetch_changes`), cria o registro do `DataSourceRun` em estado `INGESTING`, e publica as tarefas de download no Redis.
- Workers assíncronos consomem as tarefas com limite de concorrência estrito (ex: máximo de 3 downloads paralelos por Data Source), prevenindo estrangulamento de banda e saturação de taxa da API do Google.
- **Política de Retry e DLQ**:
  - Falhas transitórias (SSL drops, 429 Too Many Requests, 503 Service Unavailable) disparam até 3 retries com backoff exponencial (ex: 2s, 8s, 30s).
  - Itens que esgotarem as tentativas são movidos para a Dead Letter Queue (DLQ), sendo persistidos no `failure_summary` do `DataSourceRun` com o payload completo e o motivo detalhado do erro.
- **Gestão do Cursor**: O cursor do conector só é commitado quando o lote estiver garantido, evitando o avanço prematuro que perde itens falhados.

### 3. Visibilidade e Reprocessamento na Interface
- **Feedback no Card da Fonte de Dados**: Exibição de badge com alerta de falhas parciais (ex: *"10 de 14 arquivos falharam"*).
- **Correção da listagem de falhas**: Corrigir a leitura de propriedades no frontend (`file_name` em vez de `name`).
- **Botão de Ação "Reprocessar Falhas"**: Permitir ao usuário re-enfileirar todos os itens da DLQ de uma execução diretamente pela interface com um clique, sem precisar re-escanear a pasta inteira.

---

## Stress-Testing & Hidden Assumptions

### O que estamos assumindo como verdade:
1. **Infraestrutura**: A instância do Redis já presente no `docker-compose.yml` tem capacidade suficiente para gerenciar as filas de tarefas leves sem introduzir dependências externas pesadas (como RabbitMQ ou Celery com brokers dedicados).
2. **Autonomia da Service Account**: As falhas observadas foram estritamente originadas por concorrência de sockets TLS no cliente local, e não por revogação de permissões ou cotas de leitura da Service Account no Google Workspace.
3. **Persistência de Estado**: O modelo `DataSourceRun` em Postgres é suficiente para atuar como repositório de estado da DLQ e do progresso de reprocessamento.

### O que poderia inviabilizar esta direção:
1. **Complexidade excessiva de workers**: Adicionar processos de worker separados que exijam novos containers no Docker pode aumentar o consumo de memória em ambientes locais de desenvolvimento. *(Mitigação: Usar background workers assíncronos leves baseados em asyncio/Redis no próprio container da API ou via task runner gerenciado).*
2. **Tamanho extremo de arquivos**: Arquivos gigantes (ex: vídeos de reuniões gravadas no Drive de > 500 MB) podem estourar a memória se baixados inteiros em RAM. *(Mitigação: Streaming direto em chunks para o storage temporário ou S3/MinIO).*

### O que estamos optando por ignorar por enquanto:
- Notificações ativas via Push (Webhooks do Google Drive): O pooling incremental via `Changes API` é suficiente e muito mais simples de manter sem necessidade de expor um endpoint público para webhooks do Google.

---

## MVP Scope

### Incluído no MVP:
- [x] **Native Async Google Drive Client**: Implementação de `GoogleDriveHttpClient` usando `httpx.AsyncClient` com token Bearer da Service Account, substituindo `MediaIoBaseDownload` no conector.
- [x] **Controle de Concorrência e Retries**: Semáforo assíncrono (`asyncio.Semaphore(3)`) e política de até 3 retries com backoff para downloads com falha transitória de I/O.
- [x] **Prevenção de Avanço Prematuro de Cursor**: Se houver falhas no lote, o cursor do DataSource não avança para o novo token, preservando os itens para sincronizações futuras.
- [x] **Ajuste na UI de Falhas**: Correção da renderização de nomes de arquivos no `DataSourceRunsModal` e adição de indicador visual no `DataSourceCard`.
- [x] **Endpoint e Botão de Reprocessamento de Falhas**: Caso de uso `RetryFailedDataSourceItemsUseCase` e botão "Reprocessar Falhas" no frontend.
- [x] **Puxar os 10 arquivos pendentes**: Resetar o cursor da pasta atual e concluir a ingestão completa dos 14 itens.

### Not Doing (e por quê):
- **Celery / RabbitMQ**: Desnecessariamente complexo para a escala atual (dezenas a centenas de arquivos). Uma fila assíncrona leve usando Redis/asyncio atende com excelência e menor custo operacional.
- **Webhooks de Notificação Push do Drive**: Exige IP público/domínio exposto com certificados TLS públicos válidos para o Google conseguir enviar webhooks, o que inviabiliza desenvolvimento local e infraestruturas fechadas.
- **Reprocessamento granular item a item**: O reprocessamento em lote dos itens falhados de um run atende 99% dos casos com esforço de interface muito menor.

---

## Open Questions & Next Steps
1. Validar a migração do conector do Google Drive para o client HTTP assíncrono nativo.
2. Confirmar se iniciamos a especificação técnica formal (`SPEC-resilient-data-source-sync.md`) antes da implementação.
