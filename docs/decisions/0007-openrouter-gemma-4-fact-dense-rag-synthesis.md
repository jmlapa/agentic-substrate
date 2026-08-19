# ADR-0007: OpenRouter Gemma 4 Fact-Dense RAG Synthesis & Dual-Mode Query Architecture

## Status
Accepted

## Date
2026-08-18

## Context
1. **Substrato de Conhecimento Multiuso**: A infraestrutura atende tanto humanos (através do Frontend Console e Chatbots) quanto agentes de IA autônomos executando em loops ReAct.
2. **Prolixidade e Alucinações**: Prompts de síntese genéricos geravam saídas conversacionais prolixas ("Com base nos documentos...") com custo elevado de tokens e sem vínculo explícito aos nós ontológicos e chunks de origem.
3. **Latência Inútil em Tools de Agentes**: Agentes autônomos que usam a Knowledge Base como ferramenta de busca semântica (`retrieve`) não precisam de uma síntese em linguagem natural redundante, mas sim de acesso ultra-rápido (<30ms) ao subgrafo e aos chunks.
4. **Padronização OpenRouter com Google Gemma 4**: Conforme estabelecido no design de infraestrutura e `AppSettings`, o modelo padrão para extração estruturada de ontologia por chunk e para síntese RAG factual é o **Google Gemma 4 (`google/gemma-4-26b-a4b-it`)** via OpenRouter.

## Decision
1. **Implementação do `OpenRouterRagSynthesizer`**:
   - Criação de `OpenRouterRagSynthesizer` implementando `ILlmSynthesisService`.
   - Utilização do OpenRouter com `google/gemma-4-26b-a4b-it`, temperatura 0.1 e headers de governança (`HTTP-Referer`, `X-Title`).
   - Resolução dinâmica no `AppContainer` via `OPENROUTER_SYNTHESIS_MODEL_NAME`.
2. **Prompting Fact-Dense & Citações Estritas**:
   - Respostas em Markdown direto ao ponto, estruturadas em tópicos densos.
   - Inclusão obrigatória de referências rastreáveis `[^chunk:<id>]` e `[^entidade:<tipo>:<nome>]`.
3. **Otimização de Throughput & Supressão de Raciocínio (Reasoning)**:
   - Configuração de roteamento prioritário na OpenRouter via `provider: {"sort": "throughput", "allow_fallbacks": True}` para garantir provedores com maior vazão de tokens (ex: Parasail/Cloudflare a ~95 tok/s).
   - Supressão explícita de tokens de raciocínio com `reasoning: {"effort": "none", "exclude": True}` para evitar latência oculta.
4. **Arquitetura Dual-Mode no `QueryKnowledgeUseCase`**:
   - Suporte ao parâmetro `mode: "synthesis" | "retrieve"` nos DTOs e na API.
   - `mode == "retrieve"`: Fast-path sem acionamento de LLM, devolvendo a resposta imediatamente com todos os nós e chunks recuperados.
   - `mode == "synthesis"`: Fluxo completo de busca híbrida com síntese LLM via Gemma 4.

## Consequences
- **Agentes de IA**: Ganham uma tool de recuperação semântica pura com latência mínima e zero consumo desnecessário de tokens.
- **Usuários Humanos**: Recebem resumos claros, objetivos e com proveniência verificável no console.
- **Consistência de Modelos**: Unificação dos modelos de extração e síntese sob o OpenRouter (`google/gemma-4-26b-a4b-it`).
