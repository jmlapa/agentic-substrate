from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, create_model

from src.modules.knowledge.domain.ontology.node_type_definition import NodeTypeDefinition
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.ontology.property_definition import PropertyDefinition
from src.modules.knowledge.domain.ontology.property_type import PropertyType
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)


class DynamicOntologyModelBuilder:
    @staticmethod
    def _map_property_type_to_python(prop: PropertyDefinition) -> Any:
        if prop.enum_values:
            enum_name = f"{prop.name.capitalize()}Enum"
            return Enum(enum_name, {v: v for v in prop.enum_values})

        match prop.type:
            case PropertyType.STRING:
                return str
            case PropertyType.INTEGER:
                return int
            case PropertyType.FLOAT:
                return float
            case PropertyType.BOOLEAN:
                return bool
            case PropertyType.LIST_STRING:
                return list[str]
            case _:
                return str

    @classmethod
    def build_node_model(cls, node_def: NodeTypeDefinition) -> type[BaseModel]:
        fields: dict[str, Any] = {
            "id": (str, Field(description="Identificador único do nó no documento")),
            "node_type": (str, Field(default=node_def.name)),
        }
        for prop in node_def.properties:
            py_type = cls._map_property_type_to_python(prop)
            if prop.required:
                fields[prop.name] = (py_type, Field(description=prop.description or ""))
            else:
                fields[prop.name] = (
                    py_type | None,
                    Field(default=prop.default, description=prop.description or ""),
                )

        return create_model(f"Dynamic_{node_def.name}_Node", **fields)

    @classmethod
    def build_relationship_model(cls, rel_def: RelationshipTypeDefinition) -> type[BaseModel]:
        fields: dict[str, Any] = {
            "source_id": (str, Field(description="ID do nó de origem")),
            "target_id": (str, Field(description="ID do nó de destino")),
            "relationship_type": (str, Field(default=rel_def.name)),
        }
        for prop in rel_def.properties:
            py_type = cls._map_property_type_to_python(prop)
            if prop.required:
                fields[prop.name] = (py_type, Field(description=prop.description or ""))
            else:
                fields[prop.name] = (
                    py_type | None,
                    Field(default=prop.default, description=prop.description or ""),
                )

        return create_model(f"Dynamic_{rel_def.name}_Relationship", **fields)

    @classmethod
    def build_graph_extraction_schema(cls, ontology: OntologySchema) -> type[BaseModel]:
        fields: dict[str, Any] = {
            "nodes": (
                list[Any],
                Field(default_factory=list, description="Lista de nós extraídos"),
            ),
            "edges": (
                list[Any],
                Field(default_factory=list, description="Lista de relações"),
            ),
        }
        return create_model(f"OntologyGraph_{ontology.name}", **fields)
