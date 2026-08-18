# ADR-0007: DeepSeek-V4-Flash Fact-Dense RAG Synthesis & Dual-Mode Query Architecture

## Status
Accepted

## Date
2026-08-18

## Context
1. **Substrato de Conhecimento Multiuso**: A infraestrutura atende tanto humanos (através do Frontend Console e Chatbots) quanto agentes de IA autônomos executando em loops ReAct.
2. **Prolixidade e Alucinações**: Prompts de síntese genéricos geravam saídas conversacionais prolixas ("Com base nos documentos...") com custo elevado de tokens e sem vínculo explícito aos nós ontológicos e chunks de origem.
3. **Latência Inútil em Tools de Agentes**: Agentes autônomos que usam a Knowledge Base como ferramenta de busca semântica (`retrieve`) não precisam de uma síntese em linguagem natural redundante, mas sim de acesso ultra-rápido (<30ms) ao subgrafo e aos chunks.
4. **Padronização OpenRouter**: Conforme estabelecido no ADR-0005, o gateway padrão para extração de grafos e síntese é o OpenRouter utilizando `deepseek/deepseek-v4-flash`.

## Decision
1. **Implementação do `DeepSeekRagSynthesizer`**:
   - Criação de `DeepSeekRagSynthesizer` implementando `ILlmSynthesisService`.
   - Utilização do OpenRouter com `deepseek/deepseek-v4-flash`, temperatura 0.1 e headers de governança.
   - Substituição da instanciação padrão legada do Gemini no `AppContainer` em favor do DeepSeek quando `OPENROUTER_API_KEY` estiver configurada.
2. **Prompting Fact-Dense & Citações Estritas**:
   - Respostas em Markdown direto ao ponto, estruturadas em tópicos densos.
   - Inclusão obrigatória de referências rastreáveis `[^chunk:<uuid>]` e `[^entidade:<tipo>:<nome>]`.
3. **Arquitetura Dual-Mode no `QueryKnowledgeUseCase`**:
   - Suporte ao parâmetro `mode: "synthesis" | "retrieve"` nos DTOs e na API.
   - `mode == "retrieve"`: Fast-path sem acionamento de LLM, devolvendo a resposta imediatamente em tempo de sub-milissegundos com todos os nós e chunks recuperados.
   - `mode == "synthesis"`: Fluxo completo de busca híbrida com síntese LLM.

## Consequences
- **Agentes de IA**: Ganham uma tool de recuperação semântica pura com latência mínima e zero consumo desnecessário de tokens.
- **Usuários Humanos**: Recebem resumos claros, objetivos e com proveniência verificável no console.
- **Consistência de Infraestrutura**: Unificação dos modelos de extração e síntese sob o OpenRouter (`deepseek/deepseek-v4-flash`).
