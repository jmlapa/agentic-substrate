import pytest

from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.get_ontology_template import (
    GetOntologyTemplateRequest,
    GetOntologyTemplateUseCase,
)
from src.modules.knowledge.application.use_cases.list_ontology_templates import (
    ListOntologyTemplatesRequest,
    ListOntologyTemplatesUseCase,
)
from src.modules.knowledge.domain.ontology import (
    NodeTypeDefinition,
    OntologyTemplate,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_ontology_repository import (
    InMemoryOntologyRepository,
)


@pytest.mark.asyncio
async def test_get_and_list_ontology_templates() -> None:
    repo = InMemoryOntologyRepository()
    get_use_case = GetOntologyTemplateUseCase(repo)
    list_use_case = ListOntologyTemplatesUseCase(repo)

    # 1. Lista inicialmente vazia
    empty_list = await list_use_case.execute(ListOntologyTemplatesRequest())
    assert isinstance(empty_list, Ok)
    assert len(empty_list.value.templates) == 0

    # 2. Salvar template no repo
    template_res = OntologyTemplate.create(
        name="ontologia_trabalho",
        description="Direito do trabalho",
        version=1,
        node_types=[NodeTypeDefinition(name="Empregado", description="desc")],
        relationship_types=[],
    )
    assert isinstance(template_res, Ok)
    template = template_res.value
    await repo.save(template)

    # 3. Buscar por ID
    get_by_id_res = await get_use_case.execute(GetOntologyTemplateRequest(id=template.id))
    assert isinstance(get_by_id_res, Ok)
    assert get_by_id_res.value.name == "ontologia_trabalho"

    # 4. Buscar por Nome e Versão
    get_by_name_res = await get_use_case.execute(
        GetOntologyTemplateRequest(name="ontologia_trabalho", version=1)
    )
    assert isinstance(get_by_name_res, Ok)
    assert get_by_name_res.value.id == template.id

    # 5. Buscar com parâmetros vazios (erro)
    invalid_req = await get_use_case.execute(GetOntologyTemplateRequest())
    assert isinstance(invalid_req, Err)
    assert invalid_req.error.code == "INVALID_GET_ONTOLOGY_REQUEST"

    # 6. Listagem geral
    list_res = await list_use_case.execute(ListOntologyTemplatesRequest())
    assert isinstance(list_res, Ok)
    assert len(list_res.value.templates) == 1
    assert list_res.value.templates[0].id == template.id
