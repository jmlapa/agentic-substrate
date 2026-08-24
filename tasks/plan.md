# Implementation Plan: Markdown Continuity Normalizer (Marco 1.19)

## 1. Overview

O parser VLM (`ParallelVlmDocumentParser`) possui dois problemas conhecidos na saída do Markdown: (1) o `system_prompt` de produção está mais pobre que o POC — três regras de continuidade nunca migraram; (2) a concatenação injeta marcadores `<!-- PAGE N -->` e pode duplicar headers entre páginas. Este plano entrega o Marco 1.19 em 7 tarefas atômicas XS/S, cada uma com ciclo implement → test → commit antes de avançar. O executor DEVE usar a skill `incremental-implementation` em cada tarefa.

---

## 2. Architecture Decisions

- **Sem novos arquivos de adapter ou classes públicas** — toda lógica fica em `ParallelVlmDocumentParser` como métodos privados (`_normalize_markdown`, `_dedup_adjacent_headers`) e constantes de módulo.
- **Regex compiladas no nível de módulo** (fora da classe) para performance e testabilidade independente.
- **Deduplicação apenas entre headers adjacentes** — sem parágrafo de conteúdo entre eles (após remoção dos markers). Isso evita falsos positivos em documentos que reutilizam o mesmo título em seções diferentes.
- **Dois pontos de normalização** — fast-path de cache (L226) e path normal (L296-298) — ambos devem chamar `_normalize_markdown`.
- **Atualização atômica de assertions** — não é possível mudar apenas o teste sem aplicar o normalizer no mesmo commit (senão o teste falha ao contrário). Tasks 3 e 4 são acopladas nesse sentido.

---

## 3. Dependency Graph

```
[Task 1] Regex constants no módulo
    │
    ├── [Task 2] _dedup_adjacent_headers() + testes unitários
    │       │
    │       └── [Task 3] _normalize_markdown() + 7 testes unitários novos
    │               │
    │               └── [Task 4] Aplicar normalizer nos 2 pontos de saída
    │                       + atualizar assertions existentes (acoplado)
    │
    └── [Task 5] Enriquecer system_prompt + teste de presença das 3 regras
            │
            └── [Task 6] Atualizar docs (SPEC + CAPABILITY-MAP)
                    │
                    └── [Task 7] Gate final: make pre-commit
```

---

## 4. Phase Breakdown

### Phase 1: Fundação (Tasks 1-3)
Adiciona as constantes e métodos privados sem ainda mudar o comportamento externo. O sistema permanece funcionando e os testes existentes continuam passando.

### Phase 2: Integração (Task 4)
Liga o normalizer nos dois pontos de saída e atualiza as assertions existentes atomicamente. Após esta task, o comportamento externo muda: `parse_to_markdown` nunca mais emite `<!-- PAGE N -->`.

### Phase 3: Prompt Enrichment (Task 5)
Enriquece o `system_prompt` com as 3 regras de continuidade e valida via teste de string.

### Phase 4: Docs & Gate (Tasks 6-7)
Atualiza os docs de spec e executa o gate de qualidade completo.

---

## 5. Risks and Mitigations

| Risco | Impacto | Mitigação |
|---|---|---|
| Regex de error marker falha em exceções com texto longo | Baixo | Usar `re.DOTALL` + testar com mock de erro real |
| Deduplicação remove headers legítimos com mesmo texto em seções distintas | Médio | Dedup apenas em headers **adjacentes** (sem conteúdo entre eles) — não global |
| Testes viciados (mock retornando o resultado esperado sem testar lógica real) | Alto | Testar `_normalize_markdown` diretamente com strings fixas, sem mocks; o método é puro e determinístico |
| Executor modifica mais arquivos que o escopo da task | Médio | Cada task especifica explicitamente os arquivos; qualquer arquivo fora da lista requer confirmação |

---

## 6. Anti-Padrões Proibidos para o Executor

> ⚠️ O executor DEVE seguir a skill `incremental-implementation`. Em particular:

- **NÃO** escrever mais de ~100 linhas sem rodar os testes.
- **NÃO** criar testes que apenas verificam que a função foi chamada (mocks sem lógica real). Os testes do normalizer usam strings fixas de entrada e assertam strings fixas de saída.
- **NÃO** mockar `_normalize_markdown` nos testes unitários dela — testar a função diretamente, ela é pura.
- **NÃO** modificar arquivos fora do escopo listado na task sem confirmação explícita.
- **NÃO** commitar com testes falhando. Se um teste falhar, corrigir ANTES do commit.
- **NÃO** remover ou enfraquecer assertions existentes para fazê-las passar — entender por que falharam e corrigir o código.

---

## 7. Commit Convention

Todos os commits neste plano usam o formato Conventional Commits:
```
feat(knowledge): <descrição no imperativo>
test(knowledge): <descrição no imperativo>
docs: <descrição no imperativo>
```

Cada commit é atômico — representa exatamente uma task completa.
