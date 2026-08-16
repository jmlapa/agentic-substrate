# Lista de Tarefas: Motor de Ontologias Dinâmicas e Reutilizáveis

## Fase 1: Domínio e Contratos do Motor de Ontologia

### Tarefa 1: Criar Entidade de Domínio `OntologyTemplate`
**Descrição:** Implementar a entidade de domínio `OntologyTemplate` com identificador único, nome, versão, descrição, lista de nós e relações, e método de validação interna de integridade de grafos (impedindo arestas apontando para nós não declarados).
**Critérios de Aceite:**
- [ ] Entidade criada em `src/modules/knowledge/domain/ontology/ontology_template.py` isolada (Single Class per File).
- [ ] Validações de integridade no construtor/método de fábrica retornando `Result[OntologyTemplate, DomainError]`.
- [ ] Testes unitários cobrindo criação válida e rejeição de relações órfãs.
**Verificação:**
- [ ] `pytest tests/unit/ -k test_ontology_template`
**Dependências:** Nenhuma
**Arquivos prováveis:**
- `src/modules/knowledge/domain/ontology/ontology_template.py`
- `src/modules/knowledge/domain/ontology/__init__.py`
- `tests/unit/test_ontology_template.py`
**Escopo estimado:** S (2-3 arquivos)

---

### Tarefa 2: Criar Protocolo de Repositório `IOntologyRepository`
**Descrição:** Definir a interface de repositório no domínio para persistência e recuperação de templates de ontologia.
**Critérios de Aceite:**
- [ ] Protocolo criado em `src/modules/knowledge/domain/interfaces/i_ontology_repository.py`.
- [ ] Métodos assíncronos: `save`, `get_by_id`, `get_by_name_and_version` e `list_all`.
- [ ] Tipagem estrita sem Any.
**Verificação:**
- [ ] `mypy src/modules/knowledge/domain/interfaces/i_ontology_repository.py`
**Dependências:** Tarefa 1
**Arquivos prováveis:**
- `src/modules/knowledge/domain/interfaces/i_ontology_repository.py`
- `src/modules/knowledge/domain/interfaces/__init__.py`
**Escopo estimado:** XS (1-2 arquivos)

---

### Tarefa 3: Implementar Adaptador `InMemoryOntologyRepository`
**Descrição:** Implementar o repositório em memória para persistir e buscar instâncias de `OntologyTemplate`.
**Critérios de Aceite:**
- [ ] Classe criada em `src/modules/knowledge/infrastructure/adapters/in_memory_ontology_repository.py`.
- [ ] Implementa rigorosamente todos os métodos de `IOntologyRepository`.
- [ ] Testes unitários para todas as operações do repositório.
**Verificação:**
- [ ] `pytest tests/unit/ -k test_ontology_repository`
**Dependências:** Tarefa 2
**Arquivos prováveis:**
- `src/modules/knowledge/infrastructure/adapters/in_memory_ontology_repository.py`
- `src/modules/knowledge/infrastructure/adapters/__init__.py`
- `tests/unit/test_ontology_repository.py`
**Escopo estimado:** S (2-3 arquivos)

---

## Checkpoint 1: Domínio e Persistência
- [ ] Todos os testes da Fase 1 passando: `pytest tests/unit/ -k "ontology"`
- [ ] Checagem estrita de tipos: `mypy src/modules/knowledge`

---

## Fase 2: Casos de Uso de Gerenciamento de Ontologias

### Tarefa 4: Implementar Caso de Uso `CreateOntologyTemplateUseCase`
**Descrição:** Criar o caso de uso para registro de novas receitas de ontologia, com DTOs dedicados e tratamento de erros funcionais.
**Critérios de Aceite:**
- [ ] Pasta `src/modules/knowledge/application/use_cases/create_ontology_template/` contendo:
  - `create_ontology_template_request.py`
  - `create_ontology_template_response.py`
  - `create_ontology_template_use_case.py`
  - `__init__.py`
- [ ] Retorna `Result[CreateOntologyTemplateResponse, DomainError]`.
- [ ] Testes unitários cobrindo fluxo de sucesso e duplicidade/inconsistência.
**Verificação:**
- [ ] `pytest tests/unit/ -k test_create_ontology_template`
**Dependências:** Tarefa 3
**Arquivos prováveis:**
- `src/modules/knowledge/application/use_cases/create_ontology_template/*`
- `tests/unit/test_create_ontology_template.py`
**Escopo estimado:** M (4-5 arquivos)

---

### Tarefa 5: Implementar Casos de Uso `GetOntologyTemplateUseCase` e `ListOntologyTemplatesUseCase`
**Descrição:** Implementar os casos de uso para consulta individual e listagem de catálogo de templates de ontologia.
**Critérios de Aceite:**
- [ ] Pastas dedicadas seguindo Single Class per File:
  - `src/modules/knowledge/application/use_cases/get_ontology_template/`
  - `src/modules/knowledge/application/use_cases/list_ontology_templates/`
- [ ] Testes unitários para busca por ID e listagem geral.
**Verificação:**
- [ ] `pytest tests/unit/ -k "get_ontology or list_ontology"`
**Dependências:** Tarefa 4
**Arquivos prováveis:**
- `src/modules/knowledge/application/use_cases/get_ontology_template/*`
- `src/modules/knowledge/application/use_cases/list_ontology_templates/*`
- `tests/unit/test_get_and_list_ontology_templates.py`
**Escopo estimado:** M (5-6 arquivos)

---

## Checkpoint 2: Casos de Uso de Ontologia
- [ ] Casos de uso de CRUD de templates operacionais e testados: `pytest tests/unit/`
- [ ] Conformidade de linting: `ruff check src/modules/knowledge`

---

## Fase 3: Compilação Dinâmica para `pydantic-ai` v2 & Integração com Knowledge Base

### Tarefa 6: Aprimorar `DynamicOntologyModelBuilder` para Compilação Estrita de Enums em Memória
**Descrição:** Atualizar o gerador dinâmico de schemas Pydantic para criar classes de Enum em memória a partir de `enum_values` e garantir que o schema agregado gerado seja 100% compatível com a validação do `pydantic-ai` v2.
**Critérios de Aceite:**
- [ ] Geração dinâmica de `enum.Enum` ou `typing.Literal` para propriedades com `enum_values`.
- [ ] Validação garantida: tentativa de instanciar modelo com valor fora do enum levanta `ValidationError` do Pydantic.
- [ ] Testes unitários específicos para validação de nós e relacionamentos gerados dinamicamente.
**Verificação:**
- [ ] `pytest tests/unit/ -k test_dynamic_ontology_pydantic_builder`
**Dependências:** Tarefa 1
**Arquivos prováveis:**
- `src/modules/knowledge/infrastructure/extractors/dynamic_ontology_model_builder.py`
- `tests/unit/test_dynamic_ontology_builder.py`
**Escopo estimado:** S (2 arquivos)

---

### Tarefa 7: Integrar `CreateKnowledgeBaseUseCase` com Precedência de `ontology_id`
**Descrição:** Permitir que o caso de uso de criação de Knowledge Base receba um `ontology_id` para carregar um template existente do `IOntologyRepository`, mantendo retrocompatibilidade com declaração de schema inline.
**Critérios de Aceite:**
- [ ] Atualização de `CreateKnowledgeBaseRequest` e `CreateKnowledgeBaseUseCase`.
- [ ] Testes unitários cobrindo criação com `ontology_id` existente e com ID inexistente (retornando erro de domínio).
**Verificação:**
- [ ] `pytest tests/unit/test_knowledge_module.py`
**Dependências:** Tarefa 4, Tarefa 6
**Arquivos prováveis:**
- `src/modules/knowledge/application/use_cases/create_knowledge_base/*`
- `tests/unit/test_knowledge_module.py`
**Escopo estimado:** S (3 arquivos)

---

### Tarefa 8: Adicionar Endpoints REST no API Gateway para Catálogo de Ontologias
**Descrição:** Expor rotas FastAPI para cadastrar, listar e consultar templates de ontologia.
**Critérios de Aceite:**
- [ ] Controller `src/api_gateway/controllers/ontology_controller.py`.
- [ ] DTOs de API correspondentes em `src/api_gateway/dtos/`.
- [ ] Testes de integração via TestClient/FastAPI.
**Verificação:**
- [ ] `pytest tests/integration/`
**Dependências:** Tarefa 5, Tarefa 7
**Arquivos prováveis:**
- `src/api_gateway/controllers/ontology_controller.py`
- `src/api_gateway/dtos/create_ontology_template_dto.py`
- `src/api_gateway/main.py`
- `tests/integration/test_api_gateway.py`
**Escopo estimado:** M (4-5 arquivos)

---

## Checkpoint Final: Validação de Qualidade
- [ ] `make pre-commit` (Ruff check, Ruff format, Mypy strict, Pytest com 100% de cobertura).
