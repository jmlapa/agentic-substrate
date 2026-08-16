from uuid import UUID, uuid4

from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.entity import Entity
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.domain.ontology.node_type_definition import NodeTypeDefinition
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)


class OntologyTemplate(Entity[UUID]):
    def __init__(
        self,
        id: UUID,
        name: str,
        version: int,
        description: str,
        node_types: list[NodeTypeDefinition],
        relationship_types: list[RelationshipTypeDefinition],
    ) -> None:
        super().__init__(id)
        self._name = name
        self._version = version
        self._description = description
        self._node_types = list(node_types)
        self._relationship_types = list(relationship_types)

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> int:
        return self._version

    @property
    def description(self) -> str:
        return self._description

    @property
    def node_types(self) -> list[NodeTypeDefinition]:
        return list(self._node_types)

    @property
    def relationship_types(self) -> list[RelationshipTypeDefinition]:
        return list(self._relationship_types)

    def get_node_type(self, name: str) -> NodeTypeDefinition | None:
        return next((nt for nt in self._node_types if nt.name == name), None)

    def get_relationship_type(self, name: str) -> RelationshipTypeDefinition | None:
        return next((rt for rt in self._relationship_types if rt.name == name), None)

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        node_types: list[NodeTypeDefinition],
        relationship_types: list[RelationshipTypeDefinition],
        version: int = 1,
        id: UUID | None = None,
    ) -> Result["OntologyTemplate", DomainError]:
        if not name or not name.strip():
            return Err(
                DomainError(
                    "O nome da ontologia não pode ser vazio.",
                    "INVALID_ONTOLOGY_NAME",
                )
            )

        if version < 1:
            return Err(
                DomainError(
                    "A versão da ontologia deve ser >= 1.",
                    "INVALID_ONTOLOGY_VERSION",
                )
            )

        # Validar nós duplicados
        node_names = set()
        for node in node_types:
            if node.name in node_names:
                return Err(
                    DomainError(
                        f"Tipo de nó duplicado na ontologia: '{node.name}'.",
                        "DUPLICATE_NODE_TYPE",
                        {"node_name": node.name},
                    )
                )
            node_names.add(node.name)

        # Validar integridade referencial dos relacionamentos
        for rel in relationship_types:
            if rel.source_node_type not in node_names:
                return Err(
                    DomainError(
                        f"Nó de origem '{rel.source_node_type}' no relacionamento '{rel.name}' "
                        "não foi declarado na ontologia.",
                        "ORPHAN_RELATIONSHIP_SOURCE",
                        {"relationship": rel.name, "source_node": rel.source_node_type},
                    )
                )
            if rel.target_node_type not in node_names:
                return Err(
                    DomainError(
                        f"Nó de destino '{rel.target_node_type}' no relacionamento '{rel.name}' "
                        "não foi declarado na ontologia.",
                        "ORPHAN_RELATIONSHIP_TARGET",
                        {"relationship": rel.name, "target_node": rel.target_node_type},
                    )
                )

        template_id = id or uuid4()
        return Ok(
            cls(
                id=template_id,
                name=name.strip(),
                version=version,
                description=description.strip(),
                node_types=node_types,
                relationship_types=relationship_types,
            )
        )
