# Agentic Substrate - Rules & Instructions for AI Agents

Este documento define regras inegociáveis para qualquer agente ou desenvolvedor atuando neste repositório.

---

## 1. Regra Inegociável de Arquitetura: Single Class per File
- **Proibição de Mono-arquivos:** É expressamente proibido agrupar múltiplos casos de uso, DTOs, entidades, eventos ou adaptadores em um único arquivo.
- **1 Classe / 1 Interface / 1 DTO = 1 Arquivo:**
  - `Entity`, `ValueObject`, `AggregateRoot` ➔ cada um em seu próprio arquivo dentro de `domain/`.
  - `DomainEvent` ➔ cada evento de domínio em seu próprio arquivo (`*_event.py`).
  - `UseCase` ➔ cada caso de uso em sua própria pasta contendo `*_request.py`, `*_response.py`, `*_use_case.py` e `__init__.py`.
  - `Interfaces / Protocolos` ➔ cada protocolo em seu arquivo (`i_*.py`).
  - `Adapters de Infraestrutura` ➔ cada implementação em seu próprio arquivo (`*_adapter.py` ou nome específico).
  - `DTOs de API` ➔ cada DTO de request/response em seu arquivo em `api_gateway/dtos/`.
- Os arquivos `__init__.py` devem atuar exclusivamente como **Facades / Exportadores públicos**, nunca contendo lógica de negócio ou declarações de classes.

---

## 2. Tipagem Estrita e Qualidade de Código (Zero Erros)
- **Mypy Strict:** O projeto opera com `strict = true` no Mypy. Todo método, função e retorno DEVE ser tipado explicitamente (sem `Any` implícito).
- **Result[T, E] Pattern:** Use checagem discriminada explícita `if isinstance(res, Err): ... return res.value`.
- **Ruff:** Todo código deve passar no `ruff check .` e `ruff format --check .`.
- **Assincronia:** Toda operação de I/O, storage, eventos e casos de uso deve usar `async/await`.

---

## 3. Spec-Driven Development (SDD)
- Toda decisão arquitetural ou alteração estrutural de escopo DEVE ser refletida em:
  - `CAPABILITY-MAP.md` (Mapa de dependências e módulos).
  - `SPEC-*.md` (Especificações detalhadas dos módulos).

---

## 4. Git Workflow, Commits e Pull Requests (PRs)

### 4.1 Padrão de Commits (Conventional Commits)
- **Atômico e Focado:** Cada commit deve representar apenas uma unidade lógica de trabalho (~100 linhas).
- **Estrutura:** `<tipo>(<escopo opcional>): <descrição no imperativo>`
- **Tipos permitidos:**
  - `feat`: Nova funcionalidade/caso de uso/capacidade.
  - `fix`: Correção de bug.
  - `refactor`: Mudança interna de código sem alteração de comportamento externo.
  - `test`: Adição ou ajuste de testes.
  - `docs`: Alteração exclusiva em documentação ou artefatos de spec (`*.md`).
  - `chore`: Atualização de dependências, ferramentas ou configurações de CI/CD.
- **Exemplo:** `feat(knowledge): add structured pydantic graph extractor`

### 4.2 Estratégia de Branches
- **Trunk-Based / Short-Lived Branches:** Branches curtas (1 a 3 dias), criadas a partir de `main`.
- **Nomenclatura:**
  - `feature/<descricao-curta>` (ex: `feature/graph-extractor`)
  - `fix/<descricao-curta>` (ex: `fix/sagas-concurrency`)
  - `refactor/<descricao-curta>` (ex: `refactor/kernel-protocols`)
  - `chore/<descricao-curta>` (ex: `chore/mypy-config`)

### 4.3 Padrão de Pull Requests (PRs)
- PRs pequenos e revisáveis (< 400 linhas).
- Todo PR deve conter:
  1. **Objetivo:** O que e por que foi implementado.
  2. **Mudanças Principais:** Lista de módulos e arquivos alterados.
  3. **Validação:** Evidência de execução dos gates de qualidade (testes, mypy, ruff).
  4. **Spec Reference:** Link/referência ao `SPEC-*.md` correspondente.

---

## 5. Versionamento Semântico e Releases (SemVer & Changelog)
- **SemVer (`MAJOR.MINOR.PATCH`):**
  - `MAJOR`: Quebra de compatibilidade em contratos de API pública ou schemas de eventos.
  - `MINOR`: Novas capacidades ou rotas adicionadas de forma retrocompatível.
  - `PATCH`: Correções de bugs retrocompatíveis ou refatorações internas.
- **Tags Imutáveis:** Toda release deve ser acompanhada de uma tag Git (`vX.Y.Z`).
- **`CHANGELOG.md`:** Manter o histórico de versões baseado no formato Keep a Changelog (`Added`, `Changed`, `Fixed`, `Deprecated`, `Removed`, `Security`).

---

## 6. Gates de Verificação e Critérios de Aprovação Pré-Commit

### 6.1 Execução Automatizada via Makefile
Antes de qualquer commit, PR ou encerramento de tarefa, o gate oficial do Makefile DEVE ser executado:
```bash
make pre-commit
```

### 6.2 Checklist de Critérios de Aprovação para Commit
Para que qualquer commit ou PR seja aprovado, todos os critérios abaixo devem ser satisfeitos:
- [ ] **Linter (Ruff):** Zero erros e zero warnings de sintaxe ou imports.
- [ ] **Formatador (Ruff):** Código 100% formatado conforme as regras do projeto.
- [ ] **Tipagem Estrita (Mypy):** `mypy: No issues found` em modo estrito (sem `Any` implícito).
- [ ] **Testes Automatizados (Pytest):** 100% de testes unitários e de integração passando com medição de cobertura.
- [ ] **Single Class per File:** Nenhuma classe, DTO ou entidade agrupada em mono-arquivo.
- [ ] **Mensagem de Commit:** No formato Conventional Commits no modo imperativo.
- [ ] **Sem Segredos:** Nenhuma API key, senha ou credencial incluída no diff (`.env` ou código).
