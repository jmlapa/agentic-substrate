import pytest

from src.kernel.domain.result import Ok
from src.modules.knowledge.application.use_cases.list_knowledge_bases import (
    ListKnowledgeBasesRequest,
    ListKnowledgeBasesUseCase,
)
from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import (
    KnowledgeBaseAggregate,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)


@pytest.mark.asyncio
async def test_list_knowledge_bases_use_case() -> None:
    repo = InMemoryKnowledgeBaseRepository()
    use_case = ListKnowledgeBasesUseCase(repo)

    # 1. Lista inicialmente vazia
    empty_res = await use_case.execute(ListKnowledgeBasesRequest())
    assert isinstance(empty_res, Ok)
    assert len(empty_res.value.knowledge_bases) == 0

    # 2. Criar e salvar KBs no repositório
    schema = OntologySchema(
        name="schema_test",
        description="Schema para testes",
        node_types=[],
        relationship_types=[],
    )
    kb1 = KnowledgeBaseAggregate.create("KB Alpha", "Primeira KB de teste", schema)
    kb1.attach_document("doc1.pdf", "application/pdf")
    await repo.save(kb1)

    kb2 = KnowledgeBaseAggregate.create("KB Beta", "Segunda KB de teste", schema)
    await repo.save(kb2)

    # 3. Executar listagem
    res = await use_case.execute(ListKnowledgeBasesRequest())
    assert isinstance(res, Ok)
    assert len(res.value.knowledge_bases) == 2

    # Validar campos do DTO
    kb1_summary = next(k for k in res.value.knowledge_bases if k.id == kb1.id)
    assert kb1_summary.name == "KB Alpha"
    assert kb1_summary.description == "Primeira KB de teste"
    assert kb1_summary.status == "ACTIVE"
    assert kb1_summary.storage_partition == f"kb-{kb1.id}"
    assert kb1_summary.documents_count == 1

    kb2_summary = next(k for k in res.value.knowledge_bases if k.id == kb2.id)
    assert kb2_summary.name == "KB Beta"
    assert kb2_summary.documents_count == 0
