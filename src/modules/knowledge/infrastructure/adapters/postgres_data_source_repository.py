import json
from uuid import UUID

import asyncpg

from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.interfaces.i_data_source_repository import (
    IDataSourceRepository,
)
from src.modules.knowledge.domain.value_objects.data_source_status import (
    DataSourceStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)


class PostgresDataSourceRepository(IDataSourceRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save(self, data_source: DataSource) -> None:
        query = """
        INSERT INTO knowledge_data_sources (
            id, kb_id, name, data_source_type, status, cursor,
            sync_interval_minutes, last_synced_at, error_message,
            config, created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11, $12
        )
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            data_source_type = EXCLUDED.data_source_type,
            status = EXCLUDED.status,
            cursor = EXCLUDED.cursor,
            sync_interval_minutes = EXCLUDED.sync_interval_minutes,
            last_synced_at = EXCLUDED.last_synced_at,
            error_message = EXCLUDED.error_message,
            config = EXCLUDED.config,
            updated_at = EXCLUDED.updated_at;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                data_source.id,
                data_source.kb_id,
                data_source.name,
                str(data_source.data_source_type),
                str(data_source.status),
                data_source.cursor,
                data_source.sync_interval_minutes,
                data_source.last_synced_at,
                data_source.error_message,
                json.dumps(data_source.config),
                data_source.created_at,
                data_source.updated_at,
            )

    async def get_by_id(self, data_source_id: UUID) -> DataSource | None:
        query = """
        SELECT id, kb_id, name, data_source_type, status, cursor,
               sync_interval_minutes, last_synced_at, error_message,
               config, created_at, updated_at
        FROM knowledge_data_sources
        WHERE id = $1;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, data_source_id)
            if not row:
                return None
            return self._map_row_to_entity(row)

    async def list_by_kb_id(self, kb_id: UUID) -> list[DataSource]:
        query = """
        SELECT id, kb_id, name, data_source_type, status, cursor,
               sync_interval_minutes, last_synced_at, error_message,
               config, created_at, updated_at
        FROM knowledge_data_sources
        WHERE kb_id = $1
        ORDER BY created_at DESC;
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, kb_id)
            return [self._map_row_to_entity(r) for r in rows]

    async def delete(self, data_source_id: UUID) -> bool:
        query = "DELETE FROM knowledge_data_sources WHERE id = $1;"
        async with self._pool.acquire() as conn:
            res = await conn.execute(query, data_source_id)
            return bool(str(res).endswith("1"))

    def _map_row_to_entity(self, row: asyncpg.Record) -> DataSource:
        raw_config = row["config"]
        config_dict = (
            json.loads(raw_config) if isinstance(raw_config, str) else dict(raw_config or {})
        )
        return DataSource(
            id=row["id"],
            kb_id=row["kb_id"],
            name=row["name"],
            data_source_type=DataSourceType(row["data_source_type"]),
            status=DataSourceStatus(row["status"]),
            cursor=row["cursor"],
            sync_interval_minutes=row["sync_interval_minutes"],
            last_synced_at=row["last_synced_at"],
            error_message=row["error_message"],
            config=config_dict,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
