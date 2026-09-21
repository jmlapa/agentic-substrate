# Google Drive Knowledge Connector Pool

## Problem Statement
Como poderíamos conectar bases de conhecimento do Agentic Substrate a pastas específicas do Google Drive corporativo de forma contínua e autônoma, viabilizando ingestão histórica retroativa e sincronização periódica de novos documentos e versões, sem exigir credenciais OAuth individuais de cada usuário, sem depender de webhooks frágeis e eliminando o risco de duplicação ou inconsistência factual de dados?

---

## Recommended Direction: Folder-Bound Delta Watcher com Blue/Green Swap

### 1. Modelo de Identidade e Autenticação
- **GCP Service Account:** O conector utiliza uma única Service Account central com credenciais seguras (JSON key ou Workload Identity).
- **Zero Fricção de OAuth:** Usuários não precisam fazer login individual nem gerenciar consent screens. Basta compartilhar as pastas ou Shared Drives desejados com o endereço da Service Account (ex: `bot-knowledge@meu-projeto.iam.gserviceaccount.com`) com permissão de visualizador/leitor.

### 2. Vínculo e Escopo Declarativo (`Folder ID ➔ KB ID`)
- Cada Knowledge Base pode possuir um ou mais conectores ativos.
- O vínculo é estritamente delimitado por um ou mais `folder_id` do Google Drive:
  - **Herança de Permissões Nativa:** Todo documento ou transcrição depositado na pasta é automaticamente acessível pela Service Account.
  - **Roteamento Determinístico:** Elimina a necessidade de adivinhar ou classificar a qual KB um arquivo compartilhado pertence.

### 3. Janela de Baseline Inicial e Sincronização Periódica
- **Importação Inicial:** Ao criar a conexão, o usuário define uma janela retroativa de baseline (ex: últimos 30 dias, 90 dias ou histórico completo), filtrando por `modifiedTime >= cutoff_date`.
- **Engine de Sincronização Leve (Delta Polling):**
  - O conector armazena o `startPageToken` da API do Drive na entidade do conector.
  - O ciclo de atualização executa periodicamente via worker agendado (ex: a cada 5 a 15 minutos) ou sob demanda via endpoint HTTP (`POST /sync`).
  - Consulta `changes.list(pageToken)` para identificar apenas arquivos criados, alterados ou removidos nas pastas monitoradas.
  - Dispensa completamente webhooks públicos de push notifications, que exigiriam validação de domínio no Search Console, expiração de canais a cada 7 dias e infraestrutura complexa de renovação.

### 4. Ciclo de Vida de Versões: Blue/Green Document Atomic Swap
- Para evitar inconsistências e alucinações factuais geradas pela convivência de versões antigas e novas de um mesmo documento no GraphRAG:
  1. O conector identifica que um arquivo existente teve seu `version_hash` / `modifiedTime` alterado.
  2. Cria um novo documento na KB com metadados `replaces_doc_id = old_doc_id`.
  3. A nova versão passa por todo o pipeline da Saga de forma isolada (parsing, chunking hierárquico, embeddings Gemini e extração ontológica no FalkorDB).
  4. Durante o reprocessamento, a versão antiga permanece ativa e disponível para consultas RAG sem downtime.
  5. Ao concluir com sucesso a indexação da nova versão (`DocumentIndexedEvent`), o sistema executa o cleanup atômico da versão antiga utilizando o `DeleteDocumentUseCase` (removendo subgrafo obsoleto do FalkorDB, chunks e arquivos em storage).
  6. Em caso de falha no pipeline da nova versão, a versão antiga é preservada intacta.

### 5. Governança e Acesso
- O isolamento de acesso opera no nível da Knowledge Base. Quem possui autorização para consultar a KB tem visibilidade dos conteúdos sincronizados do Google Drive vinculados a ela.

---

## Key Assumptions to Validate
- [ ] **Exportação de Google Docs Nativos:** A Service Account consegue exportar arquivos nativos do Google (`application/vnd.google-apps.document`) para texto/markdown ou PDF via `files.export` respeitando as quotas da API.
- [ ] **Escopo de Alterações no `changes.list`:** O token delta da API do Drive filtra eficientemente apenas os eventos pertinentes às pastas configuradas, sem sobrecarga de chamadas.
- [ ] **Exclusão Limpa no FalkorDB:** A execução do `DeleteDocumentUseCase` durante o swap atômico remove nós específicos do documento sem fragmentar ou romper a integridade de entidades conceituais compartilhadas no grafo.

---

## MVP Scope

### O que está no escopo (In-Scope)
- **Entidade de Conector na KB:** Estrutura de domínio para armazenar status, tipo de conector (`google_drive`), credenciais/referência da service account, lista de `folder_ids`, janela de baseline e `last_page_token`.
- **Casos de Uso de Gerenciamento:**
  - `CreateGoogleDriveConnectorUseCase`
  - `SyncGoogleDriveConnectorUseCase` (manual ou disparado por worker)
  - `GetConnectorStatusUseCase` (saúde da conexão, último sync, total de docs sincronizados)
- **Adapter de Integração Google Drive:**
  - Descoberta e download de PDFs, áudios, imagens e arquivos de texto.
  - Conversão de Google Docs para texto plano ou PDF para alimentar o pipeline multimodal.
- **Sincronização Delta com Blue/Green Swap:**
  - Detecção de hash/data de modificação.
  - Ingestão paralela e remoção da versão predecessora após indexação concluída.

---

## Not Doing (and Why)
- **OAuth 2.0 individual (3-legged) por usuário:** Dispensado no MVP corporativo para evitar complexidade de fluxos de login, tokens de refresh, telas de consentimento e expiração de sessões de usuários.
- **Webhooks de Push Notifications (`files.watch`):** Descartado por fragilidade operacional (requer domínio público verificado no Google Search Console, túneis HTTPS rígidos e rotina de renovação semanal).
- **ACL granular por chunk/usuário no FalkorDB:** Complexidade desnecessária no MVP; a governança de acesso é delimitada pela própria Knowledge Base.
- **Diff semântico parcial de chunks:** Exigiria reconciliação probabilística complexa no grafo ontológico. O reprocessamento completo da nova versão com Blue/Green swap é determinístico, limpo e à prova de inconsistências.

---

## Open Questions
1. **Frequência de Polling Automático:** Qual a periodicidade ideal padrão para o worker de background (5 minutos vs 15 minutos) para balancear frescor de dados e quota de chamadas à API do GCP?
2. **Tratamento de Arquivos Deletados no Drive:** Quando um arquivo for removido da pasta do Google Drive, a deleção deve disparar automaticamente o `DeleteDocumentUseCase` correspondente na KB ou mover para um status de arquivamento?
