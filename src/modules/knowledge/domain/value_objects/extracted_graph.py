from pydantic import Field

from src.kernel.domain.value_object import ValueObject
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode


class ExtractedGraph(ValueObject):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
