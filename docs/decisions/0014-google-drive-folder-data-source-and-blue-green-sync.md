# ADR-0014: Conector Google Drive Folder com Service Account Central e Blue/Green Ingestion

## Status
Accepted

## Data
2026-09-22

## Contexto
O Agentic Substrate necessita ingerir e sincronizar continuamente documentos hospedados no Google Drive (PDFs, Docs, Sheets, Textos, Áudios) em Knowledge Bases com GraphRAG. Ao projetar o conector e a interface de configuração, surgiu a decisão crítica de segurança e arquitetura sobre a gestão de credenciais:
1. **Abordagem A (Upload via Web):** Permitir que cada usuário suba um arquivo `.json` de Service Account pela interface web do frontend.
2. **Abordagem B (Service Account Central no Host/VM):** Manter a Service Account configurada de forma segura na infraestrutura de backend (disco da VM e variável de ambiente `GOOGLE_APPLICATION_CREDENTIALS`), exigindo apenas que os usuários compartilhem suas pastas do Google Drive com o e-mail dessa Service Account com permissão de leitura (*Viewer*).

### Riscos da Abordagem A
- **Vazamento de Segredos de Alto Privilégio:** Chaves privadas RSA de Service Accounts do GCP trafegariam pela rede e ficariam armazenadas em banco de dados ou estado de cliente, sujeitas a vazamento por BOLA/IDOR, XSS ou logs acidentais.
- **Sobrecarga para o Usuário Final:** Exigiria que todo usuário criasse um projeto no Google Cloud Console, ativasse a Google Drive API e gerasse chaves criptográficas.

## Decisão

Adotamos a **Abordagem B (Service Account Central na Infraestrutura)** com o seguinte desenho arquitetural:

1. **Gestão Segura de Credenciais no Deploy:**
   - No deploy da VM (`deploy/vm/`), o arquivo de chave da Service Account é salvo no disco do host (ex: `deploy/vm/credentials/google-service-account.json`) com permissões restritas (`chmod 700`).
   - O `docker-compose.yml` monta esse diretório no container da API em modo somente leitura: `./credentials:/app/credentials:ro`.
   - A variável `GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-service-account.json` é configurada no `.env` e mapeada em `AppSettings`.
   - Em ambientes gerenciados no GCP (GKE, Cloud Run, Compute Engine), o conector herda automaticamente a identidade IAM da máquina via Application Default Credentials (ADC), dispensando arquivos JSON estáticos.

2. **Modelo de Autorização Baseado em Compartilhamento:**
   - Para indexar uma pasta, o usuário abre o Google Drive, clica em **Compartilhar** e adiciona o e-mail da Service Account (ex: `bot@meu-projeto.iam.gserviceaccount.com`) como **Leitor (Viewer)**.
   - O conector possui acesso somente de leitura restrito exclusivamente às pastas compartilhadas explicitamente com ele.

3. **Interface de Configuração no Frontend:**
   - No frontend, o usuário nunca manipula arquivos `.json` de credenciais.
   - O usuário apenas fornece o **Nome** e o **ID ou Link Completo da Pasta** (`https://drive.google.com/drive/folders/...`), além de parâmetros como intervalo de sync, janela inicial (baseline) e tipos de arquivo permitidos.
   - Um aviso contextual na UI explica o passo de compartilhamento da pasta com a Service Account.

4. **Ingestão Blue/Green com Delta Sync:**
   - As sincronizações ocorrem em lote isolado (*Green*).
   - Somente após o parsing, chunking, embeddings e indexação ontológica bem-sucedidos de todos os arquivos modificados, ocorre o swap atômico, superando versões anteriores de documentos na Knowledge Base sem downtime de busca.

## Consequências

### Positivas
- **Segurança Máxima:** Zero chaves privadas transitando em formulários web ou expostas no navegador.
- **Simplicidade para Usuários:** A experiência do usuário consiste em compartilhar a pasta no Drive (ação natural do Google Workspace) e colar o link no console.
- **Isolamento de Acesso:** A Service Account só enxerga pastas explicitamente compartilhadas com ela, respeitando o princípio do menor privilégio (*Least Privilege*).
- **Auditabilidade e Governança:** O administrador da infraestrutura centraliza o ciclo de vida da Service Account no GCP IAM.

### Negativas / Mitigações
- Requer uma etapa única de configuração no deploy da VM (criação da Service Account no GCP e salvamento do JSON no diretório de credenciais). Essa etapa foi totalmente documentada no `README.md`, `deploy/vm/.env.example` e nos scripts de automação.
