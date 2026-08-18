# Idea: DeepSeek-V4-Flash Fact-Dense RAG Synthesis & Dual-Payload Retrieval

## Problem Statement
Como podemos fornecer consultas de alta precisão no Substrato de Conhecimento que atendam simultaneamente agentes autônomos (que exigem dados crus e zero latência adicional) e humanos/interfaces (que exigem respostas em Markdown factual, denso e com proveniência explícita), eliminando dependências legadas e prolixidade?

---

## Recommended Direction

Implementar uma arquitetura de consulta flexível e unificada sob o **OpenRouter (`deepseek/deepseek-v4-flash`)**:

1. **`DeepSeekRagSynthesizer` (Substituindo `GeminiRagSynthesizer`)**:
   - Implementa `ILlmSynthesisService` consumindo a rota de Chat Completions do OpenRouter com o modelo `deepseek/deepseek-v4-flash`.
   - Utiliza transporte HTTP resiliente com headers de governança (`HTTP-Referer`, `X-Title`) e timeout configurável.

2. **Prompting Fact-Dense & Proveniência Explícita**:
   - O system prompt proíbe introduções e conclusões conversacionais ("Com base nos documentos fornecidos...", "Espero ter ajudado!").
   - Respostas estruturadas em tópicos densos (*Bullet Points* factuais).
   - Cada fato afirmado DEVE conter sua âncora de proveniência rastreável com o ID do Chunk ou Entidade do Grafo: `[^chunk:<uuid>]` ou `[^entidade:<tipo>:<nome>]`.

3. **Modo de Consulta Selecionável (`mode: "synthesis" | "retrieve"`)**:
   - Adicionar o campo `mode: str = "synthesis"` em `QueryKnowledgeRequest` e `QueryKnowledgeDTO`.
   - **`mode == "retrieve"` (Fast Path para Agentes / Tools)**:
     - Executa apenas a busca vetorial + expansão de subgrafo no FalkorDB.
     - `answer = ""` (ou resumo quantitativo curto).
     - Retorna em < 30ms sem gastar tokens de LLM.
   - **`mode == "synthesis"` (Padrão para Playground / Chatbots)**:
     - Executa a busca híbrida + chamada assíncrona ao `DeepSeekRagSynthesizer`.
     - Retorna o Markdown sintetizado no campo `answer` E a lista de `results` completa para inspeção de proveniência na UI.

---

## Key Assumptions to Validate
- [ ] **Aderência a Citações Estritas no DeepSeek-V4-Flash**: Validar se o modelo respeita consistentemente a sintaxe de citação `[^chunk:<id>]` sem alucinar IDs inexistentes.
- [ ] **Latência do OpenRouter**: Mensurar se o tempo de resposta do endpoint OpenRouter para o DeepSeek Flash permanece abaixo de 800ms para sínteses com top-k=5.
- [ ] **Compatibilidade Retroativa de API**: Garantir que requisições antigas sem o campo `mode` continuem funcionando com valor padrão (`synthesis`).

---

## MVP Scope

### In Scope
- Criação de `DeepSeekRagSynthesizer` em `src/modules/knowledge/infrastructure/adapters/deepseek_rag_synthesizer.py`.
- Atualização de `QueryKnowledgeRequest`, `QueryKnowledgeDTO` e `QueryKnowledgeUseCase` para suportar `mode: "synthesis" | "retrieve"`.
- Atualização do `container.py` para injetar `DeepSeekRagSynthesizer` usando `settings.openrouter_api_key` e `settings.openrouter_graph_model_name`.
- Testes unitários para `DeepSeekRagSynthesizer` e para o branch de execução do `QueryKnowledgeUseCase` com `mode="retrieve"`.
- Atualização do `QueryPlaygroundView.tsx` no frontend para suportar o toggle `Modo: Síntese Completa | Apenas Recuperação (Raw)`.

### Out of Scope (Not Doing & Why)
- **Streaming de Tokens via Server-Sent Events (SSE)**: Mantido fora do MVP para não quebrar a arquitetura atômica de Result Pattern dos casos de uso atuais; será introduzido em fase posterior específica de streaming.
- **Reranker de Cross-Encoder Local**: FalkorDB HNSW + Cypher traversal já fornecem ordenação e pontuação híbrida suficiente para a janela de contexto atual.
- **Remoção de `GeminiEmbeddingAdapter`**: O Gemini continua sendo usado exclusivamente para Embeddings (768d MRL), pois a qualidade/custo de embedding do Gemini 2 é superior e já está estabilizada.

---

## Open Questions
- O formato de citação `[^chunk:<uuid>]` deve ser renderizado como link interativo no Playground frontend para focar o chunk correspondente no inspetor?
- Desejamos expor a temperatura do sintetizador no request ou fixá-la em 0.1/0.2 para máxima determinância?
