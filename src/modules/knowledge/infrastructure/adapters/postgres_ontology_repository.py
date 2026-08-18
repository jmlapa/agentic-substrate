import json
from uuid import UUID

import asyncpg
from pydantic import TypeAdapter

from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)
from src.modules.knowledge.domain.ontology.node_type_definition import (
    NodeTypeDefinition,
)
from src.modules.knowledge.domain.ontology.ontology_template import OntologyTemplate
from src.modules.knowledge.domain.ontology.relationship_type_definition import (
    RelationshipTypeDefinition,
)


class PostgresOntologyRepository(IOntologyRepository):
    """
    Adaptador de persistência de templates de ontologia no PostgreSQL.
    Armazena entidades e relações em colunas JSONB com tipagem estrita.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._node_types_adapter: TypeAdapter[list[NodeTypeDefinition]] = TypeAdapter(
            list[NodeTypeDefinition]
        )
        self._rel_types_adapter: TypeAdapter[list[RelationshipTypeDefinition]] = TypeAdapter(
            list[RelationshipTypeDefinition]
        )

    async def save(self, ontology: OntologyTemplate) -> None:
        query = """
        INSERT INTO ontology_templates (
            id, name, description, version, node_types, relationship_types, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5::jsonb, $6::jsonb, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            version = EXCLUDED.version,
            node_types = EXCLUDED.node_types,
            relationship_types = EXCLUDED.relationship_types,
            updated_at = NOW();
        """
        node_types_json = json.dumps([n.model_dump() for n in ontology.node_types])
        rel_types_json = json.dumps([r.model_dump() for r in ontology.relationship_types])

        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                ontology.id,
                ontology.name,
                ontology.description,
                ontology.version,
                node_types_json,
                rel_types_json,
            )

    async def get_by_id(self, id: UUID) -> OntologyTemplate | None:
        query = """
        SELECT id, name, description, version, node_types, relationship_types
        FROM ontology_templates
        WHERE id = $1;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, id)
            if not row:
                return None
            return self._row_to_entity(row)

    async def get_by_name_and_version(self, name: str, version: int) -> OntologyTemplate | None:
        query = """
        SELECT id, name, description, version, node_types, relationship_types
        FROM ontology_templates
        WHERE name = $1 AND version = $2;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, name, version)
            if not row:
                return None
            return self._row_to_entity(row)

    async def list_all(self) -> list[OntologyTemplate]:
        query = """
        SELECT id, name, description, version, node_types, relationship_types
        FROM ontology_templates
        ORDER BY created_at DESC;
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [self._row_to_entity(r) for r in rows]

    def _row_to_entity(self, row: asyncpg.Record) -> OntologyTemplate:
        raw_nodes = row["node_types"]
        raw_rels = row["relationship_types"]

        node_types = (
            self._node_types_adapter.validate_json(raw_nodes)
            if isinstance(raw_nodes, str)
            else self._node_types_adapter.validate_python(raw_nodes)
        )
        rel_types = (
            self._rel_types_adapter.validate_json(raw_rels)
            if isinstance(raw_rels, str)
            else self._rel_types_adapter.validate_python(raw_rels)
        )

        return OntologyTemplate(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            version=row["version"],
            node_types=node_types,
            relationship_types=rel_types,
        )
