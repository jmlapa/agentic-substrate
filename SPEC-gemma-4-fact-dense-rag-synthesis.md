# SPEC: OpenRouter Gemma 4 Fact-Dense RAG Synthesis & Dual-Payload Retrieval

## Overview & Scope
Este documento especifica a arquitetura e os contratos de consulta do **Substrato de Conhecimento**, introduzindo a síntese de respostas baseada no modelo **Google Gemma 4 (`google/gemma-4-26b-a4b-it`)** via gateway OpenRouter com saída em **Fact-Dense Markdown** e suporte a **modo dual (`synthesis` vs `retrieve`)**.

---

## 1. Arquitetura de Consulta e Dual-Payload

O endpoint de consulta híbrida (`POST /api/v1/knowledge/bases/{kb_id}/query`) atende dois perfis distintos de consumidores:

```text
                                  ┌────────────────────────┐
                                  │   POST /bases/{id}/query│
                                  │  {query, top_k, mode}  │
                                  └───────────┬────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │     QueryKnowledgeUseCase       │
                             │ (Busca Híbrida FalkorDB Grafo)  │
                             └────────┬───────────────┬────────┘
                                      │               │
                 mode == "retrieve"   │               │   mode == "synthesis"
             (Fast-Path p/ Agentes)   │               │   (Console / Chatbots)
                                      ▼               ▼
                       ┌────────────────────┐   ┌───────────────────────────┐
                       │ Retorno Imediato   │   │ OpenRouterRagSynthesizer  │
                       │ < 30ms / 0 tokens  │   │ OpenRouter (Gemma 4 26B)  │
                       └────────┬───────────┘   └─────────────┬─────────────┘
                                │                             │
                                └──────────────┬──────────────┘
                                               ▼
                               ┌───────────────────────────────┐
                               │     QueryKnowledgeResponse    │
                               │   - answer (Fact-Dense MD)    │
                               │   - results (Chunks & Grafo)  │
                               └───────────────────────────────┘
```

---

## 2. Contrato de DTOs e Casos de Uso

### Request DTO (`QueryKnowledgeDTO` / `QueryKnowledgeRequest`)
* `query` (str): Pergunta em linguagem natural.
* `top_k` (int, 1 a 20, default 3): Quantidade máxima de evidências a recuperar.
* `max_tokens_budget` (int, 50 a 32000, default 3500): Orçamento dinâmico de tokens do contexto de entrada.
* `mode` (str, default `"synthesis"`):
  * `"synthesis"`: Executa recuperação híbrida vetorial/grafo + síntese com `OpenRouterRagSynthesizer` (Gemma 4).
  * `"retrieve"`: Executa apenas a recuperação estruturada no FalkorDB sem chamada a LLM.

### Response DTO (`QueryKnowledgeResponse`)
* `answer` (str):
  * No modo `synthesis`: Resposta densa em Markdown contendo citações rastreáveis (`[^chunk:<uuid>]`, `[^entidade:<tipo>:<nome>]`).
  * No modo `retrieve`: Mensagem quantitativa de evidências recuperadas.
* `results` (list[`HybridSearchResult`]): Lista completa dos chunks textuais, score de similaridade, `header_path`, navegação (`prev_chunk_id`/`next_chunk_id`) e triplas ontológicas.
* `total_tokens_estimated` (int): Total de tokens do contexto recuperado.
* `retrieval_trace` (dict): Metadados de auditoria e telemetria da recuperação.

---

## 3. Adaptador `OpenRouterRagSynthesizer`

* **Modelo:** `google/gemma-4-26b-a4b-it` via OpenRouter.
* **Configuração:** Temperatura 0.1, `max_tokens: 800`.
* **Roteamento de Provedor & Throughput:** `provider: {"sort": "throughput", "allow_fallbacks": True}`, roteando dinamicamente para os clusters mais rápidos da OpenRouter (ex: Parasail/Cloudflare a ~95 tok/s).
* **Supressão de Reasoning:** `reasoning: {"effort": "none", "exclude": True}`, garantindo zero tokens e latência oculta de raciocínio.
* **Prompt System:** Formatação estrita Fact-Dense em tópicos, proibindo enrolações conversacionais, forçando citações explícitas de proveniência (`[^chunk:<id>]`) e proibindo categoricamente o uso de conhecimento prévio externo caso as evidências recuperadas sejam insuficientes ou irrelevantes (emitindo declaração explícita de ausência de informações).
