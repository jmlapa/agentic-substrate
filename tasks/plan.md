# Plano de Implementação: Motor de Ontologias Dinâmicas e Reutilizáveis (Ontology Engine)

## Visão Geral
Implementar o subsistema de Ontologias como cidadão de primeira classe dentro do módulo `knowledge`. Isso inclui o modelo de domínio de templates de ontologia (`OntologyTemplate`), repositório de persistência, validação de integridade referencial de grafos, casos de uso de gerenciamento de templates (criação, consulta, listagem), aprimoramento do compilador dinâmico de modelos Pydantic com suporte completo a Enums dinâmicos em memória para `pydantic-ai` v2, e integração com o fluxo de criação de Knowledge Base.

---

## Decisões Arquiteturais e Padrões
1. **Clean Architecture & Single Class per File:** Cada classe, DTO, interface e caso de uso residirá em seu próprio arquivo isolado.
2. **Tipagem Estrita com Mypy:** Toda assinatura e retorno com tipos explícitos (`strict = true`).
3. **Padrão Result[T, E]:** Tratamento explícito de erros com `Ok` e `Err(DomainError)`.
4. **Geração Dinâmica de Enums em Memória:** Uso nativo de `enum.Enum` dinâmico integrado ao `pydantic.create_model` para alimentar o `result_type` do `pydantic-ai` sem gerar arquivos estáticos.
5. **Precedência de Ontologia:** Criação de Knowledge Base passa a aceitar `ontology_id` para reuso de receitas de ontologia pré-existentes.

---

## Estrutura do Grafo de Dependências
```
Domain: OntologyTemplate & VOs
    │
    ├── Domain: IOntologyRepository Protocol
    │       │
    │       ├── Infrastructure: InMemoryOntologyRepository
    │       │
    │       └── Application: Use Cases (Create, Get, List Ontology Template)
    │
    └── Infrastructure: DynamicOntologyModelBuilder (Runtime Enum/Pydantic Compilation)
            │
            └── Application/Integration: CreateKnowledgeBaseUseCase (vinculação por ontology_id)
```

---

## Fases de Implementação e Tarefas

### Fase 1: Domínio e Contratos do Motor de Ontologia
- **Tarefa 1:** Criar a entidade de domínio `OntologyTemplate` com validação de topologia e integridade referencial.
- **Tarefa 2:** Criar a interface de repositório `IOntologyRepository` no domínio.
- **Tarefa 3:** Implementar o adaptador `InMemoryOntologyRepository` na infraestrutura.

### Ponto de Verificação 1: Domínio & Persistência Base
- [ ] Testes unitários do domínio `OntologyTemplate` passando (validações de nós, arestas órfãs e versionamento).
- [ ] Repositório em memória testado e tipado rigorosamente.

### Fase 2: Casos de Uso de Gerenciamento de Ontologias
- **Tarefa 4:** Implementar o caso de uso `CreateOntologyTemplateUseCase` (com request, response e testes).
- **Tarefa 5:** Implementar os casos de uso `GetOntologyTemplateUseCase` e `ListOntologyTemplatesUseCase` (com requests, responses e testes).

### Ponto de Verificação 2: Casos de Uso da Aplicação
- [ ] Casos de uso de criação, busca e listagem de templates operacionais com 100% de cobertura.

### Fase 3: Compilação Dinâmica para `pydantic-ai` v2 & Integração com Knowledge Base
- **Tarefa 6:** Aprimorar `DynamicOntologyModelBuilder` para suportar compilação dinâmica de Enums com validação estrita e testes de rejeição a valores inválidos.
- **Tarefa 7:** Atualizar `CreateKnowledgeBaseUseCase` para suportar criação via `ontology_id` existente com fallback para schema inline.
- **Tarefa 8:** Atualizar endpoints no `api_gateway` (ou controllers) para expor a gestão de templates de ontologia.

### Ponto de Verificação 3: Integração & Qualidade Total
- [ ] `make pre-commit` executado com sucesso (Ruff check, Ruff format, Mypy strict, Pytest com 100% de cobertura).
- [ ] Fluxo ponta a ponta: Cadastro de Template -> Criação de KB vinculada -> Compilação de schema para IA validada.

---

## Riscos e Mitigações
| Risco | Impacto | Mitigação |
|---|---|---|
| Arestas conectando nós inexistentes na ontologia | Alto | Validação no método de fábrica/construtor do `OntologyTemplate` antes de salvar. |
| Incompatibilidade de nomes de Enums dinâmicos | Médio | Normalização e sanitização de identificadores de enum para caracteres válidos em Python. |
| Quebra de retrocompatibilidade com KBs antigas | Médio | Manter suporte opcional a ontologia inline no DTO de criação de KB. |
