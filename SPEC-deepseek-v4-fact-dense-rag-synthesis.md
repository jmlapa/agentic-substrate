# SPEC: DeepSeek-V4-Flash Fact-Dense RAG Synthesis & Dual-Payload Retrieval

## Overview & Scope
Este documento especifica a arquitetura e os contratos de consulta do **Substrato de Conhecimento**, introduzindo a síntese de respostas baseada no modelo **DeepSeek-V4-Flash** via gateway OpenRouter com saída em **Fact-Dense Markdown** e suporte a **modo dual (`synthesis` vs `retrieve`)**.

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
                       │ Retorno Imediato   │   │ DeepSeekRagSynthesizer    │
                       │ < 30ms / 0 tokens  │   │ OpenRouter (DeepSeek v4)  │
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
* `top_k` (int, 1 a 50, default 5): Quantidade máxima de evidências a recuperar.
* `mode` (str, default `"synthesis"`):
  * `"synthesis"`: Executa recuperação híbrida vetorial/grafo + síntese com `DeepSeekRagSynthesizer`.
  * `"retrieve"`: Executa apenas a recuperação estruturada no FalkorDB sem chamada a LLM.

### Response DTO (`QueryKnowledgeResponse`)
* `answer` (str):
  * No modo `synthesis`: Resposta densa em Markdown contendo citações rastreáveis (`[^chunk:<uuid>]`, `[^entidade:<tipo>:<nome>]`).
  * No modo `retrieve`: Mensagem quantitativa de evidências recuperadas.
* `results` (list[`HybridSearchResult`]): Lista completa dos chunks textuais, score de similaridade, `header_path` e subgrafos conceituais recuperados.

---

## 3. Adaptador `DeepSeekRagSynthesizer`

* **Interface Implementada:** [`ILlmSynthesisService`](src/modules/knowledge/domain/interfaces/i_llm_synthesis_service.py).
* **Provedor:** OpenRouter API (`https://openrouter.ai/api/v1/chat/completions`).
* **Modelo Padrão:** `deepseek/deepseek-v4-flash` (via `OPENROUTER_GRAPH_MODEL_NAME`).
* **Hiperparâmetros:** `temperature = 0.1` (alta determinância e fidelidade).
* **Governância:** Headers `HTTP-Referer` e `X-Title` injetados automaticamente.
* **Prompting Fact-Dense:**
  * Proibição estrita de preâmbulos e conclusões conversacionais.
  * Tópicos estruturados (*bullet points*) e tabelas.
  * Citação obrigatória para cada afirmação factual.
