from uuid import uuid4

import pytest

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)
from src.modules.knowledge.domain.ontology.node_type_definition import (
    NodeTypeDefinition,
)
from src.modules.knowledge.domain.ontology.ontology_schema import (
    OntologySchema,
)
from src.modules.knowledge.domain.ontology.property_definition import (
    PropertyDefinition,
)
from src.modules.knowledge.domain.ontology.property_type import PropertyType
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)
from src.modules.knowledge.domain.value_objects.canonical_entity import (
    CanonicalEntity,
)
from src.modules.knowledge.infrastructure.extractors.existing_entity_registry import (
    ExistingEntityRegistry,
)
from src.modules.knowledge.infrastructure.extractors.pydantic_ai_graph_extractor import (
    PydanticAiGraphExtractor,
)


@pytest.fixture
def sample_ontology() -> OntologySchema:
    return OntologySchema(
        name="LegalOntology",
        description="Ontologia jurídica",
        node_types=[
            NodeTypeDefinition(
                name="Norma",
                description="Norma legal ou regulamentar",
                properties=[
                    PropertyDefinition(name="numero", type=PropertyType.STRING, required=True)
                ],
            ),
            NodeTypeDefinition(
                name="Orgao",
                description="Órgão público ou tribunal",
                properties=[
                    PropertyDefinition(name="sigla", type=PropertyType.STRING, required=False)
                ],
            ),
        ],
        relationship_types=[
            RelationshipTypeDefinition(
                name="REGULA",
                description="Regula as competências do órgão",
                source_node_type="Norma",
                target_node_type="Orgao",
            )
        ],
    )


@pytest.mark.asyncio
async def test_pydantic_ai_extractor_fallback_mode(sample_ontology: OntologySchema) -> None:
    limiter = AsyncTokenBucketLimiter()
    registry = ExistingEntityRegistry()
    extractor = PydanticAiGraphExtractor(
        rate_limiter=limiter,
        entity_registry=registry,
        api_key=None,
    )

    kb_id = uuid4()
    markdown = "# CF88\nA Norma da CF88 regula o Orgao STF."

    graph = await extractor.extract_graph(markdown, sample_ontology, kb_id=kb_id)

    assert len(graph.nodes) >= 2
    assert any(n.node_type == "Norma" for n in graph.nodes)
    assert any(n.node_type == "Orgao" for n in graph.nodes)
    assert len(graph.edges) >= 1

    # Valida que as entidades foram registradas no catálogo
    entities = await registry.get_all_distinct(kb_id)
    assert len(entities) >= 2


def test_build_system_prompt_with_known_entities(sample_ontology: OntologySchema) -> None:
    extractor = PydanticAiGraphExtractor()
    known = [
        CanonicalEntity(
            id="org_stf",
            name="Supremo Tribunal Federal",
            entity_type="Orgao",
            aliases=["STF", "Supremo"],
        )
    ]

    prompt = extractor._build_system_prompt(sample_ontology, known)
    assert "LegalOntology" in prompt
    assert "org_stf" in prompt
    assert "Supremo Tribunal Federal" in prompt
    assert "STF" in prompt
    assert "CATÁLOGO DE ENTIDADES CONHECIDAS" in prompt
