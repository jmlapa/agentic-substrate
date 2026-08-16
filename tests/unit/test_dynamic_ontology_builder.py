from typing import Any

import pytest
from pydantic import ValidationError

from src.kernel.domain.result import Ok
from src.modules.knowledge.domain.ontology import (
    NodeTypeDefinition,
    OntologyTemplate,
    PropertyDefinition,
    PropertyType,
    RelationshipTypeDefinition,
)
from src.modules.knowledge.infrastructure.extractors.dynamic_ontology_model_builder import (
    DynamicOntologyModelBuilder,
)


def test_dynamic_ontology_enum_validation() -> None:
    # 1. Criar ontologia com propriedade enum restrita
    node_def = NodeTypeDefinition(
        name="DiretivaSubordinacao",
        description="Diretiva de subordinação do empregador",
        properties=[
            PropertyDefinition(
                name="tipo_controle",
                type=PropertyType.STRING,
                required=True,
                enum_values=["escala", "meta_obrigatoria", "advertencia"],
            ),
            PropertyDefinition(
                name="impacto",
                type=PropertyType.STRING,
                required=False,
                enum_values=["alto", "medio", "baixo"],
                default="medio",
            ),
        ],
    )

    builder = DynamicOntologyModelBuilder()
    dynamic_model = builder.build_node_model(node_def)

    # 2. Instanciação com valores válidos do Enum
    valid_instance: Any = dynamic_model(
        id="dir-01",
        tipo_controle="escala",
        impacto="alto",
    )
    assert valid_instance.id == "dir-01"
    assert valid_instance.tipo_controle == "escala"
    assert valid_instance.impacto == "alto"

    # 3. Teste do valor default do Enum
    default_instance: Any = dynamic_model(
        id="dir-02",
        tipo_controle="meta_obrigatoria",
    )
    assert default_instance.impacto == "medio"

    # 4. Rejeição de valor fora do Enum (erro de validação do Pydantic)
    with pytest.raises(ValidationError) as exc_info:
        dynamic_model(
            id="dir-03",
            tipo_controle="opcao_invalida_alucinada_por_llm",
        )
    assert "tipo_controle" in str(exc_info.value)


def test_dynamic_graph_extraction_schema_with_template() -> None:
    template_res = OntologyTemplate.create(
        name="direito_trabalhista",
        description="Ontologia trabalhista",
        node_types=[
            NodeTypeDefinition(
                name="Trabalhador",
                description="Trabalhador",
                properties=[
                    PropertyDefinition(name="cpf", type=PropertyType.STRING, required=True)
                ],
            )
        ],
        relationship_types=[
            RelationshipTypeDefinition(
                name="PRESTA_SERVICO",
                description="Prestação",
                source_node_type="Trabalhador",
                target_node_type="Trabalhador",
            )
        ],
    )
    assert isinstance(template_res, Ok)
    template = template_res.value

    builder = DynamicOntologyModelBuilder()
    graph_schema = builder.build_graph_extraction_schema(template)

    instance: Any = graph_schema(nodes=[], edges=[])
    assert instance.nodes == []
    assert instance.edges == []
