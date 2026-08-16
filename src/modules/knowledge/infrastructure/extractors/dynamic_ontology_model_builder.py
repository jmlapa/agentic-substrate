import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, create_model

from src.modules.knowledge.domain.ontology.node_type_definition import NodeTypeDefinition
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.ontology.ontology_template import OntologyTemplate
from src.modules.knowledge.domain.ontology.property_definition import PropertyDefinition
from src.modules.knowledge.domain.ontology.property_type import PropertyType
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)


class DynamicOntologyModelBuilder:
    @staticmethod
    def _sanitize_name(name: str) -> str:
        # Remove caracteres inválidos para identificador Python
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        if not cleaned or cleaned[0].isdigit():
            cleaned = f"Field_{cleaned}"
        return cleaned

    @classmethod
    def _map_property_type_to_python(cls, prop: PropertyDefinition) -> Any:
        if prop.enum_values:
            sanitized_name = cls._sanitize_name(prop.name.capitalize())
            enum_dict = {cls._sanitize_name(v).upper(): v for v in prop.enum_values}
            # Criar StrEnum dinâmico para interoperabilidade perfeita com Pydantic e strings
            return StrEnum(f"{sanitized_name}Enum", enum_dict)

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

        sanitized_model_name = cls._sanitize_name(node_def.name)
        return create_model(f"Dynamic_{sanitized_model_name}_Node", **fields)

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

        sanitized_rel_name = cls._sanitize_name(rel_def.name)
        return create_model(f"Dynamic_{sanitized_rel_name}_Relationship", **fields)

    @classmethod
    def build_graph_extraction_schema(
        cls, ontology: OntologySchema | OntologyTemplate
    ) -> type[BaseModel]:
        # Cria modelos específicos de cada nó e aresta
        node_models = [cls.build_node_model(nt) for nt in ontology.node_types]
        rel_models = [cls.build_relationship_model(rt) for rt in ontology.relationship_types]

        node_union = Any if not node_models else Any
        rel_union = Any if not rel_models else Any

        fields: dict[str, Any] = {
            "nodes": (
                list[node_union],  # type: ignore[valid-type]
                Field(default_factory=list, description="Lista de nós extraídos"),
            ),
            "edges": (
                list[rel_union],  # type: ignore[valid-type]
                Field(default_factory=list, description="Lista de relações"),
            ),
        }
        sanitized_ont_name = cls._sanitize_name(ontology.name)
        return create_model(f"OntologyGraph_{sanitized_ont_name}", **fields)
