import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)
from src.modules.knowledge.domain.interfaces.i_graph_extractor import (
    IGraphExtractor,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.extracted_graph import (
    ExtractedGraph,
)
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.infrastructure.adapters.openrouter_client_factory import (
    OpenRouterClientFactory,
)
from src.modules.knowledge.infrastructure.adapters.openrouter_provider_defaults import (
    OpenRouterProviderDefaults,
)
from src.modules.knowledge.infrastructure.extractors.structured_pydantic_graph_extractor import (
    StructuredPydanticGraphExtractor,
)

logger = logging.getLogger(__name__)


class _DirectEntityItem(BaseModel):
    id: str = Field(description="Normalized unique entity ID (e.g. 'art_5', 'stf', 'lei_8112')")
    name: str = Field(default="", description="Canonical display name of the entity")
    entity_type: str = Field(default="", description="Exact entity type matching the ontology")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Extracted node properties"
    )
    aliases: list[str] = Field(default_factory=list, description="Synonyms or acronyms")

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_entity(cls, data: Any) -> Any:
        if isinstance(data, dict):
            ent_type = data.get("entity_type") or data.get("type") or data.get("node_type") or ""
            raw_id = data.get("id", "")
            name = (
                data.get("name")
                or data.get("label")
                or data.get("rotulo")
                or data.get("sigla")
                or data.get("ementa")
                or raw_id
            )
            aliases = data.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]

            raw_props = data.get("properties")
            props: dict[str, Any] = dict(raw_props) if isinstance(raw_props, dict) else {}
            # Captura propriedades planas adicionais geradas pelo LLM
            for k, v in data.items():
                if k not in {
                    "id",
                    "name",
                    "label",
                    "entity_type",
                    "node_type",
                    "type",
                    "properties",
                    "aliases",
                }:
                    props[k] = v

            return {
                "id": str(raw_id),
                "name": str(name),
                "entity_type": str(ent_type),
                "properties": props,
                "aliases": aliases,
            }
        return data


class _DirectRelationItem(BaseModel):
    source_id: str = Field(description="Source entity ID")
    target_id: str = Field(description="Target entity ID")
    relationship_type: str = Field(default="", description="Relationship name matching ontology")
    properties: dict[str, Any] = Field(default_factory=dict, description="Relation properties")

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_relation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            rel_type = (
                data.get("relationship_type")
                or data.get("type")
                or data.get("relation")
                or data.get("name")
                or ""
            )
            raw_props = data.get("properties")
            props: dict[str, Any] = dict(raw_props) if isinstance(raw_props, dict) else {}
            for k, v in data.items():
                if k not in {
                    "source_id",
                    "target_id",
                    "relationship_type",
                    "relation",
                    "name",
                    "type",
                    "properties",
                }:
                    props[k] = v

            return {
                "source_id": str(data.get("source_id", "")),
                "target_id": str(data.get("target_id", "")),
                "relationship_type": str(rel_type),
                "properties": props,
            }
        return data


class _DirectGraphOutput(BaseModel):
    entities: list[_DirectEntityItem] = Field(default_factory=list)
    relations: list[_DirectRelationItem] = Field(default_factory=list)


class DirectOpenRouterGraphExtractor(IGraphExtractor):
    """
    Extrator ontológico direto de alta velocidade para OpenRouter.
    Elimina overhead de frameworks agênticos utilizando chamadas de completion diretas
    com structured outputs JSON em sub-segundos.
    """

    def __init__(
        self,
        model_name: str = "meta-llama/llama-3.1-8b-instruct",
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        app_title: str = "Agentic Substrate",
        app_referer: str = "https://agentic-substrate.local",
        rate_limiter: AsyncTokenBucketLimiter | None = None,
        max_concurrency: int = 50,
        temperature: float = 0.0,
    ) -> None:
        self._model_name = model_name
        self._api_key = api_key
        self._base_url = base_url
        self._app_title = app_title
        self._app_referer = app_referer
        self._rate_limiter = rate_limiter or AsyncTokenBucketLimiter()
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self._temperature = temperature
        self._client = OpenRouterClientFactory.create_async(
            api_key=api_key,
            base_url=base_url,
            app_title=app_title,
            app_referer=app_referer,
        )
        self._fallback_extractor = StructuredPydanticGraphExtractor()

    def _build_system_prompt(self, ontology: OntologySchema) -> str:
        lines = [
            "Você é um extrator de Knowledge Graphs de altíssima precisão.",
            f"Ontologia Alvo: {ontology.name}",
            f"Descrição: {ontology.description or 'Sem descrição'}",
            "",
            "--- TIPOS DE NÓS (ENTIDADES) PERMITIDOS ---",
        ]
        for nt in ontology.node_types:
            props = ", ".join(f"{p.name} ({p.type.value})" for p in nt.properties)
            lines.append(f"- {nt.name}: {nt.description or ''} [Propriedades: {props}]")

        lines.append("\n--- TIPOS DE RELAÇÕES PERMITIDAS ---")
        for rt in ontology.relationship_types:
            desc = rt.description or ""
            lines.append(
                f"- ({rt.source_node_type}) -[{rt.name}]-> ({rt.target_node_type}): {desc}"
            )

        lines.append(
            "\nREGRAS CRÍTICAS:\n"
            "1. Extraia APENAS nós e relações presentes no texto que respeitem a ontologia.\n"
            "2. Todo 'source_id' e 'target_id' DEVE corresponder a um 'id' em 'entities'.\n"
            "3. Use IDs normalizados em minúsculas (ex: 'lei_8112', 'art_5', 'stf').\n"
            "4. Responda ESTRITAMENTE em formato JSON com 'entities' e 'relations'.\n"
            "Exemplo:\n"
            '{\n  "entities": [{"id": "stf", "type": "SujeitoDireito", "sigla": "STF"}],\n'
            '  "relations": [{"source_id": "art_102", "target_id": "stf", "type": "JULGA_ACAO"}]\n}'
        )
        return "\n".join(lines)

    async def extract_graph(
        self,
        markdown_text: str,
        ontology: OntologySchema,
        kb_id: UUID | None = None,
    ) -> ExtractedGraph:
        if not self._client or not self._api_key:
            return await self._fallback_extractor.extract_graph(markdown_text, ontology, kb_id)

        system_prompt = self._build_system_prompt(ontology)
        user_prompt = (
            "Extraia o Knowledge Graph do texto a seguir respeitando a ontologia fornecida:\n\n"
            f"```markdown\n{markdown_text}\n```"
        )

        async with self._semaphore:
            estimated_tokens = len(system_prompt.split()) + len(user_prompt.split()) + 500
            await self._rate_limiter.acquire(estimated_tokens=estimated_tokens)

            try:
                response = await self._client.chat.completions.create(
                    model=self._model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self._temperature,
                    response_format={"type": "json_object"},
                    extra_body=OpenRouterProviderDefaults.get_throughput_extra_body(),
                )

                choice = response.choices[0]
                content = choice.message.content or "{}"
                data = json.loads(content)
                parsed = _DirectGraphOutput.model_validate(data)

                # Validação e conversão para entidades de domínio
                nodes: list[GraphNode] = []
                valid_node_ids: set[str] = set()

                for ent in parsed.entities:
                    clean_id = ent.id.strip().lower()
                    if not clean_id:
                        continue
                    valid_node_ids.add(clean_id)
                    props = dict(ent.properties)
                    props["name"] = ent.name or clean_id
                    if ent.aliases:
                        props["aliases"] = ent.aliases

                    nodes.append(
                        GraphNode(
                            id=clean_id,
                            node_type=ent.entity_type,
                            properties=props,
                        )
                    )

                edges: list[GraphEdge] = []
                for rel in parsed.relations:
                    src_id = rel.source_id.strip().lower()
                    tgt_id = rel.target_id.strip().lower()

                    # Integridade referencial básica
                    if src_id in valid_node_ids and tgt_id in valid_node_ids:
                        edges.append(
                            GraphEdge(
                                source_id=src_id,
                                target_id=tgt_id,
                                relationship_type=rel.relationship_type,
                                properties=rel.properties,
                            )
                        )

                return ExtractedGraph(nodes=nodes, edges=edges)

            except Exception as e:
                logger.warning(
                    f"Falha na extração direta com {self._model_name}: {e}. Ativando fallback."
                )
                return await self._fallback_extractor.extract_graph(markdown_text, ontology, kb_id)
