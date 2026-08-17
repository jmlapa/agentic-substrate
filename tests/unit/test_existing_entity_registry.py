from uuid import uuid4

import pytest

from src.modules.knowledge.domain.value_objects.canonical_entity import (
    CanonicalEntity,
)
from src.modules.knowledge.infrastructure.extractors.existing_entity_registry import (
    ExistingEntityRegistry,
)


@pytest.mark.asyncio
async def test_entity_registry_registration_and_lookup() -> None:
    registry = ExistingEntityRegistry()
    kb_id = uuid4()

    entity = CanonicalEntity(
        id="org_stf",
        name="Supremo Tribunal Federal",
        entity_type="Órgão",
        aliases=["STF", "Supremo"],
    )

    registered = await registry.register_entity(kb_id, entity)
    assert registered.id == "org_stf"
    assert "STF" in registered.aliases

    # Busca exata por nome
    found_by_name = await registry.find_matching(kb_id, "Supremo Tribunal Federal", "Órgão")
    assert found_by_name is not None
    assert found_by_name.id == "org_stf"

    # Busca por alias sem acento e minúsculas
    found_by_alias = await registry.find_matching(kb_id, "stf", "orgao")
    assert found_by_alias is not None
    assert found_by_alias.id == "org_stf"


@pytest.mark.asyncio
async def test_entity_registry_merge_aliases() -> None:
    registry = ExistingEntityRegistry()
    kb_id = uuid4()

    entity1 = CanonicalEntity(
        id="lei_8112",
        name="Lei 8.112",
        entity_type="Norma",
        aliases=["Estatuto dos Servidores"],
    )
    await registry.register_entity(kb_id, entity1)

    # Registra a mesma entidade com novos aliases
    entity2 = CanonicalEntity(
        id="lei_8112",
        name="Lei 8.112",
        entity_type="Norma",
        aliases=["Regime Jurídico Único", "RJU"],
    )
    merged = await registry.register_entity(kb_id, entity2)

    assert "RJU" in merged.aliases
    assert "Estatuto dos Servidores" in merged.aliases

    found = await registry.find_matching(kb_id, "rju", "norma")
    assert found is not None
    assert found.id == "lei_8112"


@pytest.mark.asyncio
async def test_entity_registry_isolation_between_kbs() -> None:
    registry = ExistingEntityRegistry()
    kb1 = uuid4()
    kb2 = uuid4()

    entity = CanonicalEntity(
        id="inst_1",
        name="Ministério Público",
        entity_type="Instituição",
        aliases=["MP"],
    )
    await registry.register_entity(kb1, entity)

    assert await registry.find_matching(kb1, "MP", "Instituição") is not None
    assert await registry.find_matching(kb2, "MP", "Instituição") is None
