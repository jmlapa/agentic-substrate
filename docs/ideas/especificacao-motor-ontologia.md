# Especificação: Motor de Ontologias Dinâmicas e Reutilizáveis (Ontology Engine)

## 1. Declaração do Problema (How Might We)
Como podemos estruturar e persistir ontologias reutilizáveis com tipagem estrita de nós, propriedades, enums e arestas, de forma que possam ser compiladas dinamicamente em tempo de execução (runtime) em schemas Pydantic para orientar e restringir o comportamento de agentes de IA (`pydantic-ai` v2) e evitar ruídos ou duplicações na base de grafos?

---

## 2. Decisões Arquiteturais e Fundamentos

### 2.1 Enums em Memória (Sem geração de arquivos estáticos em disco)
- Propriedades com domínio finito (`enum_values: list[str]`) são compiladas dinamicamente em runtime através de `enum.Enum` ou `typing.Literal`.
- As classes Pydantic dos nós e relações são geradas em runtime via `pydantic.create_model`.
- O `pydantic-ai` v2 recebe essas classes dinâmicas como `result_type`, forçando a LLM a retornar JSON Schemas válidos restritos aos enums declarados, eliminando sinônimos ambíguos na origem.

### 2.2 Ontologia como Cidadão de Primeira Classe (Receitas Reutilizáveis)
- A ontologia é desacoplada da Base de Conhecimento (KB), possuindo ciclo de vida, repositório (`IOntologyRepository`) e versionamento próprios (`OntologyTemplate`).
- Uma Knowledge Base pode ser criada apontando para um `ontology_id` pré-existente ou declarando um schema inline que é automaticamente persistido.

### 2.3 Regra de Arquitetura: Single Class per File & Strict Typing
- Cada Entidade, Value Object, Protocolo de Repositório, DTO de Request/Response e Caso de Uso reside em seu arquivo dedicado.
- Tipagem estrita com `mypy strict` e tratamento de erros funcionais com `Result[T, E]`.

---

## 3. Modelo de Domínio (`src/modules/knowledge/domain/ontology/`)

### 3.1 Entidades e Value Objects
- **`OntologyTemplate` (`ontology_template.py` - Entidade/Aggregate):**
  - `id: UUID`: Identificador único.
  - `name: str`: Nome único canônico (ex: `"direito_trabalhista_clt"`).
  - `version: int`: Versão semântica inteira incremental (ex: `1`).
  - `description: str`: Contexto geral do domínio.
  - `node_types: list[NodeTypeDefinition]`: Tipos de nós permitidos.
  - `relationship_types: list[RelationshipTypeDefinition]`: Tipos de arestas permitidas.
  - Métodos de domínio para validação de integridade referencial (relações só podem conectar nós declarados).
- **`NodeTypeDefinition` (`node_type_definition.py` - Value Object):**
  - `name: str`: Nome canônico do nó.
  - `description: str`: Descrição para guiar o extrator de IA.
  - `properties: list[PropertyDefinition]`: Atributos do nó.
- **`RelationshipTypeDefinition` (`relationship_type_definition.py` - Value Object):**
  - `name: str`: Identificador do relacionamento (ex: `"SUBORDINADO_A"`).
  - `description: str`: Descrição semântica da relação.
  - `source_node_type: str`: Nome do nó de origem.
  - `target_node_type: str`: Nome do nó de destino.
  - `properties: list[PropertyDefinition]`: Atributos da aresta.
- **`PropertyDefinition` (`property_definition.py` - Value Object):**
  - `name: str`: Nome da propriedade.
  - `type: PropertyType`: Tipo primitivo (`STRING`, `INTEGER`, `FLOAT`, `BOOLEAN`, `LIST_STRING`).
  - `description: str | None`: Instrução contextual para a IA.
  - `required: bool`: Obrigatoriedade.
  - `default: Any | None`: Valor padrão se opcional.
  - `enum_values: list[str] | None`: Lista de valores fechados para geração do Enum dinâmico.

---

## 4. Contratos de Infraestrutura (Portas de Domínio)

- **`IOntologyRepository` (`domain/interfaces/i_ontology_repository.py`):**
  - `async def save(self, ontology: OntologyTemplate) -> None`
  - `async def get_by_id(self, id: UUID) -> OntologyTemplate | None`
  - `async def get_by_name_and_version(self, name: str, version: int) -> OntologyTemplate | None`
  - `async def list_all(self) -> list[OntologyTemplate]`

---

## 5. Casos de Uso da Aplicação (`src/modules/knowledge/application/use_cases/`)

1. **`create_ontology_template/`:**
   - `create_ontology_template_request.py`: DTO de entrada.
   - `create_ontology_template_response.py`: DTO de saída.
   - `create_ontology_template_use_case.py`: Criação com validação de topologia e persistência no repositório.
2. **`get_ontology_template/`:**
   - `get_ontology_template_request.py`
   - `get_ontology_template_response.py`
   - `get_ontology_template_use_case.py`
3. **`list_ontology_templates/`:**
   - `list_ontology_templates_request.py`
   - `list_ontology_templates_response.py`
   - `list_ontology_templates_use_case.py`
4. **Atualização do `create_knowledge_base/`:**
   - Suporte a `ontology_id` (vinculando a um template persistido) ou `inline_ontology`.

---

## 6. Camada de Compilação Dinâmica para `pydantic-ai` v2 (`infrastructure/extractors/`)

- **`DynamicOntologyModelBuilder` (`dynamic_ontology_model_builder.py`):**
  - `build_node_model(node_def)`: Converte definições de propriedades em campos com tipagem estrita ou `Enum` dinâmico em memória.
  - `build_relationship_model(rel_def)`: Converte definições de relações em modelos Pydantic com validação de nós de origem/destino.
  - `build_graph_extraction_schema(ontology)`: Converte o `OntologyTemplate` completo em um modelo agregador de saída para ser passado diretamente ao `Agent(result_type=...)` do `pydantic-ai`.

---

## 7. Critérios de Aceite e Verificação
- [ ] Validação estrita de integridade referencial (erro de domínio ao cadastrar relação apontando para nó inexistente).
- [ ] Geração determinística de Enums em runtime para campos com `enum_values`.
- [ ] Rejeição de valores fora do Enum pelo Pydantic gerado.
- [ ] CRUD e consulta de templates de ontologia funcionando com 100% de testes unitários.
- [ ] Ingestão e criação de Knowledge Base integradas referenciando `ontology_id`.
