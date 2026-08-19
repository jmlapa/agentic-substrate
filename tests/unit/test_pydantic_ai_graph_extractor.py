from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.kernel.infrastructure.async_token_bucket_limiter import AsyncTokenBucketLimiter
from src.modules.knowledge.domain.ontology import (
    NodeTypeDefinition,
    OntologySchema,
    PropertyDefinition,
    PropertyType,
    RelationshipTypeDefinition,
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
        name="TechOntology",
        description="Ontologia de infraestrutura",
        node_types=[
            NodeTypeDefinition(
                name="Server",
                description="Servidor cloud",
                properties=[
                    PropertyDefinition(name="hostname", type=PropertyType.STRING, required=True),
                ],
            )
        ],
        relationship_types=[
            RelationshipTypeDefinition(
                name="HOSTS",
                description="Hospeda serviço",
                source_node_type="Server",
                target_node_type="Server",
            )
        ],
    )


@pytest.mark.asyncio
async def test_pydantic_ai_graph_extractor_fallback_when_no_api_key(
    sample_ontology: OntologySchema,
) -> None:
    extractor = PydanticAiGraphExtractor(api_key=None)
    graph = await extractor.extract_graph(
        markdown_text="Server web-01 hosts database-01.",
        ontology=sample_ontology,
    )
    assert graph is not None


@pytest.mark.asyncio
async def test_pydantic_ai_graph_extractor_with_openrouter_provider(
    sample_ontology: OntologySchema,
) -> None:
    registry = ExistingEntityRegistry()
    limiter = AsyncTokenBucketLimiter(max_rpm=100)

    extractor = PydanticAiGraphExtractor(
        provider_type="openrouter",
        model_name="google/gemma-4-26b-a4b-it",
        api_key="sk-or-fake-key",
        rate_limiter=limiter,
        entity_registry=registry,
        app_title="Agentic Substrate Test",
        app_referer="https://test.local",
    )

    # Mock the internal agent run
    mock_output = MagicMock()
    mock_entity = MagicMock()
    mock_entity.id = "srv_web_01"
    mock_entity.name = "web-01"
    mock_entity.entity_type = "Server"
    mock_entity.properties = {"hostname": "web-01.internal"}
    mock_entity.aliases = ["web-01"]

    mock_relation = MagicMock()
    mock_relation.source_id = "srv_web_01"
    mock_relation.target_id = "srv_db_01"
    mock_relation.relationship_type = "HOSTS"
    mock_relation.properties = {}

    mock_output.entities = [mock_entity]
    mock_output.relations = [mock_relation]

    mock_run_result = MagicMock()
    mock_run_result.output = mock_output

    with patch("pydantic_ai.Agent.run", new_callable=AsyncMock) as mock_agent_run:
        mock_agent_run.return_value = mock_run_result

        graph = await extractor.extract_graph(
            markdown_text="Server web-01 hosts db-01.",
            ontology=sample_ontology,
        )

        assert len(graph.nodes) == 1
        assert graph.nodes[0].id == "srv_web_01"
        assert graph.nodes[0].node_type == "Server"
        assert len(graph.edges) == 1
        assert graph.edges[0].relationship_type == "HOSTS"

        # Verify registry recorded the entity
        recorded = await registry.get_all_distinct(extractor._default_kb_id)
        assert any(e.id == "srv_web_01" for e in recorded)
