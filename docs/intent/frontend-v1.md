# Statement of Intent: Frontend Console V1 (Agentic Substrate)

## Declaração de Intenção Confirmada

- **Outcome:** Uma aplicação SPA moderna e leve no diretório `/frontend`, integrada ao Agentic Substrate para gerenciar o ciclo de vida completo de Knowledge Bases e Ontologias, provendo:
  1. **Gestão de Ontologias:** Criação avulsa e reutilizável via formulário estruturado (entidades, propriedades/atributos e relacionamentos).
  2. **Gestão de Knowledge Bases:** Criação de KBs com seleção de ontologia existente ou criação inline, listagem e detalhes.
  3. **Ingestão & Monitoramento:** Upload de documentos (PDF, TXT, MD, etc.) com acompanhamento visual das etapas do pipeline GraphRAG em tempo real/polling (status por fase, contagem de nós/arestas e logs de erro).
  4. **Playground de Consulta (RAG):** Interface interativa para consultar a KB com síntese de resposta via LLM e inspeção do subgrafo e chunks recuperados.
- **User:** Desenvolvedores e operadores técnicos da plataforma, com arquitetura preparada para distribuição *open-source self-hosted*.
- **Why now:** Fechar o ciclo visual ponta a ponta da plataforma (modelagem ➔ ingestão ➔ monitoramento ➔ consulta com LLM) sem atrito manual de cURL/Postman.
- **Success:** Execução do fluxo completo na UI em poucos minutos: cadastrar ontologia ➔ criar KB ➔ subir arquivo ➔ acompanhar término das etapas ➔ perguntar no playground e receber resposta sintetizada por LLM com dados do grafo.
- **Constraint:**
  - Monorepo no diretório `/frontend`.
  - Stack: **Vite + React (TypeScript) + Tailwind CSS**.
  - Deploy conteinerizado ultra-leve no `docker-compose.yml` (servidor Node alpine ou Nginx).
  - Backend: Complementar endpoints de listagem de KBs e síntese de resposta RAG com LLM no FastAPI.
- **Out of scope (V1):** Autenticação/login, RBAC e gestão de membros/times, renderização interativa 3D/canvas pesada de grafos e multi-tenancy avançado.
