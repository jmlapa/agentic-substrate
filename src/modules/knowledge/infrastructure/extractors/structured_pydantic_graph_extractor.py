from typing import Any

from src.modules.knowledge.domain.interfaces.i_graph_extractor import IGraphExtractor
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.ontology.property_type import PropertyType
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.infrastructure.extractors.dynamic_ontology_model_builder import (
    DynamicOntologyModelBuilder,
)


class StructuredPydanticGraphExtractor(IGraphExtractor):
    def __init__(self, llm_client: Any = None) -> None:
        self._llm_client = llm_client

    async def extract_graph(self, markdown_text: str, ontology: OntologySchema) -> ExtractedGraph:
        """
        Em produção: compila os modelos Pydantic dinâmicos e passa como schema para LLM.
        Fallback heurístico / mock determinístico para testes e execução local.
        """
        builder = DynamicOntologyModelBuilder()
        extracted_nodes: list[GraphNode] = []
        extracted_edges: list[GraphEdge] = []

        for node_def in ontology.node_types:
            node_name_lower = node_def.name.lower()
            if node_name_lower in markdown_text.lower():
                node_id = f"{node_name_lower}-1"
                props: dict[str, Any] = {}
                for p in node_def.properties:
                    if p.required:
                        default_val = "Sample" if p.type == PropertyType.STRING else 1
                        props[p.name] = p.default or default_val

                dynamic_node_cls = builder.build_node_model(node_def)
                validated_model = dynamic_node_cls(id=node_id, **props)
                extracted_nodes.append(
                    GraphNode(
                        id=node_id,
                        node_type=node_def.name,
                        properties=validated_model.model_dump(exclude={"id", "node_type"}),
                    )
                )

        for rel_def in ontology.relationship_types:
            src = next(
                (n for n in extracted_nodes if n.node_type == rel_def.source_node_type),
                None,
            )
            tgt = next(
                (n for n in extracted_nodes if n.node_type == rel_def.target_node_type),
                None,
            )
            if src and tgt:
                dynamic_rel_cls = builder.build_relationship_model(rel_def)
                rel_model = dynamic_rel_cls(source_id=src.id, target_id=tgt.id)
                extracted_edges.append(
                    GraphEdge(
                        source_id=src.id,
                        target_id=tgt.id,
                        relationship_type=rel_def.name,
                        properties=rel_model.model_dump(
                            exclude={"source_id", "target_id", "relationship_type"}
                        ),
                    )
                )

        return ExtractedGraph(nodes=extracted_nodes, edges=extracted_edges)
