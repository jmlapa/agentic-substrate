import pytest

from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.domain.ontology import (
    NodeTypeDefinition,
    OntologyTemplate,
    PropertyDefinition,
    PropertyType,
    RelationshipTypeDefinition,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_ontology_repository import (
    InMemoryOntologyRepository,
)


@pytest.fixture
def valid_labor_ontology() -> OntologyTemplate:
    res = OntologyTemplate.create(
        name="direito_trabalhista_clt",
        description="Ontologia para validação de vínculo de emprego CLT",
        version=1,
        node_types=[
            NodeTypeDefinition(
                name="Trabalhador",
                description="Pessoa física prestadora de serviços",
                properties=[
                    PropertyDefinition(
                        name="cpf",
                        type=PropertyType.STRING,
                        required=True,
                    ),
                    PropertyDefinition(
                        name="funcao",
                        type=PropertyType.STRING,
                        required=False,
                    ),
                ],
            ),
            NodeTypeDefinition(
                name="TomadorServico",
                description="Empresa ou pessoa física contratante",
                properties=[
                    PropertyDefinition(
                        name="cnpj",
                        type=PropertyType.STRING,
                        required=False,
                    )
                ],
            ),
            NodeTypeDefinition(
                name="DiretivaSubordinacao",
                description="Ordens diretas, controle de jornada ou punições",
                properties=[
                    PropertyDefinition(
                        name="tipo_controle",
                        type=PropertyType.STRING,
                        required=True,
                        enum_values=[
                            "escala",
                            "meta_obrigatoria",
                            "advertencia",
                            "diretiva_direta",
                        ],
                    )
                ],
            ),
        ],
        relationship_types=[
            RelationshipTypeDefinition(
                name="EMITIU_DIRETIVA",
                description="Tomador emitiu ordem ao trabalhador",
                source_node_type="TomadorServico",
                target_node_type="DiretivaSubordinacao",
            ),
            RelationshipTypeDefinition(
                name="SUBORDINADO_A",
                description="Trabalhador subordinado ao tomador",
                source_node_type="Trabalhador",
                target_node_type="TomadorServico",
            ),
        ],
    )
    assert isinstance(res, Ok)
    return res.value


def test_ontology_template_creation_success(valid_labor_ontology: OntologyTemplate) -> None:
    assert valid_labor_ontology.name == "direito_trabalhista_clt"
    assert valid_labor_ontology.version == 1
    assert len(valid_labor_ontology.node_types) == 3
    assert len(valid_labor_ontology.relationship_types) == 2
    assert valid_labor_ontology.get_node_type("Trabalhador") is not None
    assert valid_labor_ontology.get_relationship_type("SUBORDINADO_A") is not None


def test_ontology_template_rejects_duplicate_nodes() -> None:
    res = OntologyTemplate.create(
        name="invalid_ontology",
        description="Teste de duplicidade",
        node_types=[
            NodeTypeDefinition(name="NodeA", description="desc 1"),
            NodeTypeDefinition(name="NodeA", description="desc 2"),
        ],
        relationship_types=[],
    )
    assert isinstance(res, Err)
    assert res.error.code == "DUPLICATE_NODE_TYPE"


def test_ontology_template_rejects_orphan_relationships() -> None:
    # Origem órfã
    res_source = OntologyTemplate.create(
        name="invalid_rel_source",
        description="Teste de relação órfã na origem",
        node_types=[NodeTypeDefinition(name="NodeB", description="desc")],
        relationship_types=[
            RelationshipTypeDefinition(
                name="REL_INVALID",
                description="desc",
                source_node_type="InexistentNode",
                target_node_type="NodeB",
            )
        ],
    )
    assert isinstance(res_source, Err)
    assert res_source.error.code == "ORPHAN_RELATIONSHIP_SOURCE"

    # Destino órfão
    res_target = OntologyTemplate.create(
        name="invalid_rel_target",
        description="Teste de relação órfã no destino",
        node_types=[NodeTypeDefinition(name="NodeA", description="desc")],
        relationship_types=[
            RelationshipTypeDefinition(
                name="REL_INVALID",
                description="desc",
                source_node_type="NodeA",
                target_node_type="InexistentNode",
            )
        ],
    )
    assert isinstance(res_target, Err)
    assert res_target.error.code == "ORPHAN_RELATIONSHIP_TARGET"


@pytest.mark.asyncio
async def test_in_memory_ontology_repository(valid_labor_ontology: OntologyTemplate) -> None:
    repo = InMemoryOntologyRepository()
    await repo.save(valid_labor_ontology)

    # Busca por ID
    found_by_id = await repo.get_by_id(valid_labor_ontology.id)
    assert found_by_id is not None
    assert found_by_id.id == valid_labor_ontology.id
    assert found_by_id.name == "direito_trabalhista_clt"

    # Busca por Nome e Versão
    found_by_name = await repo.get_by_name_and_version("direito_trabalhista_clt", 1)
    assert found_by_name is not None
    assert found_by_name.id == valid_labor_ontology.id

    # Listagem geral
    all_templates = await repo.list_all()
    assert len(all_templates) == 1
