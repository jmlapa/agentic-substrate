import pytest

from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.create_ontology_template import (
    CreateOntologyTemplateRequest,
    CreateOntologyTemplateUseCase,
)
from src.modules.knowledge.domain.ontology import (
    NodeTypeDefinition,
    PropertyDefinition,
    PropertyType,
    RelationshipTypeDefinition,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_ontology_repository import (
    InMemoryOntologyRepository,
)


@pytest.mark.asyncio
async def test_create_ontology_template_use_case_success() -> None:
    repo = InMemoryOntologyRepository()
    use_case = CreateOntologyTemplateUseCase(repo)

    req = CreateOntologyTemplateRequest(
        name="direito_trabalhista_clt",
        description="Ontologia trabalhista",
        version=1,
        node_types=[
            NodeTypeDefinition(
                name="Trabalhador",
                description="Trabalhador",
                properties=[
                    PropertyDefinition(
                        name="cpf",
                        type=PropertyType.STRING,
                    )
                ],
            ),
            NodeTypeDefinition(
                name="Empresa",
                description="Tomador de servico",
            ),
        ],
        relationship_types=[
            RelationshipTypeDefinition(
                name="PRESTA_SERVICO",
                description="Relacao de prestacao",
                source_node_type="Trabalhador",
                target_node_type="Empresa",
            )
        ],
    )

    res = await use_case.execute(req)
    assert isinstance(res, Ok)
    assert res.value.name == "direito_trabalhista_clt"
    assert res.value.version == 1
    assert len(res.value.node_types) == 2

    # Verificar persistencia no repo
    saved = await repo.get_by_id(res.value.id)
    assert saved is not None
    assert saved.name == "direito_trabalhista_clt"


@pytest.mark.asyncio
async def test_create_ontology_template_use_case_duplicate_name_and_version() -> None:
    repo = InMemoryOntologyRepository()
    use_case = CreateOntologyTemplateUseCase(repo)

    req = CreateOntologyTemplateRequest(
        name="ontologia_teste",
        description="teste",
        version=1,
        node_types=[NodeTypeDefinition(name="Node1", description="desc")],
        relationship_types=[],
    )

    res1 = await use_case.execute(req)
    assert isinstance(res1, Ok)

    # Tentar criar novamente mesma versao
    res2 = await use_case.execute(req)
    assert isinstance(res2, Err)
    assert res2.error.code == "ONTOLOGY_ALREADY_EXISTS"
