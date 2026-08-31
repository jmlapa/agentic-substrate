import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.modules.knowledge.domain.ontology.node_type_definition import (
    NodeTypeDefinition,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.ontology.property_definition import (
    PropertyDefinition,
)
from src.modules.knowledge.domain.ontology.property_type import PropertyType
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)
from src.modules.knowledge.infrastructure.extractors.direct_openrouter_graph_extractor import (
    DirectOpenRouterGraphExtractor,
)


@pytest.fixture
def sample_ontology() -> OntologySchema:
    return OntologySchema(
        name="TestLegalOntology",
        description="Ontologia de teste",
        node_types=[
            NodeTypeDefinition(
                name="AtoNormativo",
                description="Leis e decretos",
                properties=[
                    PropertyDefinition(name="tipo", type=PropertyType.STRING, required=True),
                ],
            ),
            NodeTypeDefinition(
                name="SujeitoDireito",
                description="Pessoas e tribunais",
                properties=[
                    PropertyDefinition(name="sigla", type=PropertyType.STRING, required=False),
                ],
            ),
        ],
        relationship_types=[
            RelationshipTypeDefinition(
                name="EDITOU",
                source_node_type="SujeitoDireito",
                target_node_type="AtoNormativo",
                description="O sujeito editou o ato",
            )
        ],
    )


@pytest.mark.asyncio
async def test_direct_extractor_fallback_when_no_api_key(
    sample_ontology: OntologySchema,
) -> None:
    extractor = DirectOpenRouterGraphExtractor(api_key=None)
    text = "AtoNormativo e SujeitoDireito no texto"
    graph = await extractor.extract_graph(text, sample_ontology)

    assert len(graph.nodes) >= 1
    assert any(n.node_type == "AtoNormativo" for n in graph.nodes)


@pytest.mark.asyncio
async def test_direct_extractor_successful_json_completion(
    sample_ontology: OntologySchema,
) -> None:
    extractor = DirectOpenRouterGraphExtractor(
        api_key="test-api-key",
        model_name="meta-llama/llama-3.1-8b-instruct",
    )

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(
        {
            "entities": [
                {
                    "id": "stf",
                    "name": "Supremo Tribunal Federal",
                    "entity_type": "SujeitoDireito",
                    "properties": {"sigla": "STF"},
                    "aliases": ["Supremo"],
                },
                {
                    "id": "lei_8112",
                    "name": "Lei 8.112/90",
                    "entity_type": "AtoNormativo",
                    "properties": {"tipo": "Lei Ordinária"},
                    "aliases": [],
                },
            ],
            "relations": [
                {
                    "source_id": "stf",
                    "target_id": "lei_8112",
                    "relationship_type": "EDITOU",
                    "properties": {},
                }
            ],
        }
    )
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    extractor._client = mock_client

    kb_id = uuid4()
    graph = await extractor.extract_graph("O STF editou a Lei 8.112.", sample_ontology, kb_id)

    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "extra_body" in call_kwargs
    assert call_kwargs["extra_body"]["provider"]["sort"] == "throughput"
    assert call_kwargs["extra_body"]["provider"]["allow_fallbacks"] is True

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.nodes[0].id == "stf"
    assert graph.nodes[0].properties["name"] == "Supremo Tribunal Federal"
    assert graph.nodes[0].properties["aliases"] == ["Supremo"]
    assert graph.edges[0].source_id == "stf"
    assert graph.edges[0].target_id == "lei_8112"
    assert graph.edges[0].relationship_type == "EDITOU"


@pytest.mark.asyncio
async def test_direct_extractor_filters_orphan_edges(
    sample_ontology: OntologySchema,
) -> None:
    extractor = DirectOpenRouterGraphExtractor(
        api_key="test-api-key",
    )

    mock_response = MagicMock()
    mock_choice = MagicMock()
    # Aresta apontando para nó inexistente "inexistente_id"
    mock_choice.message.content = json.dumps(
        {
            "entities": [
                {
                    "id": "stf",
                    "name": "Supremo Tribunal Federal",
                    "entity_type": "SujeitoDireito",
                    "properties": {},
                    "aliases": [],
                }
            ],
            "relations": [
                {
                    "source_id": "stf",
                    "target_id": "inexistente_id",
                    "relationship_type": "EDITOU",
                    "properties": {},
                }
            ],
        }
    )
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    extractor._client = mock_client

    graph = await extractor.extract_graph("Texto de teste", sample_ontology)

    assert len(graph.nodes) == 1
    assert len(graph.edges) == 0  # Aresta órfã deve ter sido descartada


@pytest.mark.asyncio
async def test_direct_extractor_retry_on_transient_error(
    sample_ontology: OntologySchema,
) -> None:
    extractor = DirectOpenRouterGraphExtractor(
        api_key="test-api-key",
    )

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(
        {
            "entities": [
                {
                    "id": "stf",
                    "name": "STF",
                    "entity_type": "SujeitoDireito",
                    "properties": {},
                    "aliases": [],
                }
            ],
            "relations": [],
        }
    )
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            Exception("Rate limit 429"),
            mock_response,
        ]
    )
    extractor._client = mock_client

    graph = await extractor.extract_graph("STF decidiu.", sample_ontology)

    assert len(graph.nodes) == 1
    assert graph.nodes[0].id == "stf"
    assert mock_client.chat.completions.create.call_count == 2
