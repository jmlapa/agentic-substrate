import asyncio
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.google import GoogleProvider

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)
from src.kernel.infrastructure.rate_limited_async_transport import (
    RateLimitedAsyncTransport,
)
from src.modules.knowledge.domain.interfaces.i_entity_registry import (
    IEntityRegistry,
)
from src.modules.knowledge.domain.interfaces.i_graph_extractor import (
    IGraphExtractor,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.canonical_entity import (
    CanonicalEntity,
)
from src.modules.knowledge.domain.value_objects.extracted_graph import (
    ExtractedGraph,
)
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.infrastructure.adapters.pydantic_ai_openrouter_provider_factory import (
    PydanticAiOpenRouterProviderFactory,
)
from src.modules.knowledge.infrastructure.extractors.existing_entity_registry import (
    ExistingEntityRegistry,
)
from src.modules.knowledge.infrastructure.extractors.structured_pydantic_graph_extractor import (
    StructuredPydanticGraphExtractor,
)


class _ExtractedEntityItem(BaseModel):
    id: str = Field(description="Identificador único normalizado (ex: org_stf, art_5, lei_8112)")
    name: str = Field(description="Nome canônico da entidade")
    entity_type: str = Field(description="Tipo da entidade conforme ontologia")
    properties: dict[str, Any] = Field(default_factory=dict, description="Propriedades da entidade")
    aliases: list[str] = Field(
        default_factory=list, description="Sinônimos e siglas encontradas no texto"
    )


class _ExtractedRelationItem(BaseModel):
    source_id: str = Field(description="ID do nó de origem")
    target_id: str = Field(description="ID do nó de destino")
    relationship_type: str = Field(description="Tipo da relação conforme ontologia")
    properties: dict[str, Any] = Field(default_factory=dict, description="Propriedades da relação")


class _GraphExtractionOutput(BaseModel):
    entities: list[_ExtractedEntityItem] = Field(default_factory=list)
    relations: list[_ExtractedRelationItem] = Field(default_factory=list)


class PydanticAiGraphExtractor(IGraphExtractor):
    """
    Extrator ontológico de grafos com PydanticAI v2 compatível com OpenRouter e Gemini.
    Possui controle de RPM/TPM via RateLimitedAsyncTransport e canonização de entidades.
    """

    def __init__(
        self,
        rate_limiter: AsyncTokenBucketLimiter | None = None,
        entity_registry: IEntityRegistry | None = None,
        provider_type: Literal["gemini", "openrouter"] = "openrouter",
        model_name: str = "deepseek/deepseek-v4-flash",
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        app_title: str = "Agentic Substrate",
        app_referer: str = "https://agentic-substrate.local",
        max_concurrency: int = 15,
    ) -> None:
        self._limiter = rate_limiter or AsyncTokenBucketLimiter()
        self._registry = entity_registry or ExistingEntityRegistry()
        self._provider_type = provider_type
        self._model_name = model_name
        self._api_key = api_key
        self._base_url = base_url
        self._app_title = app_title
        self._app_referer = app_referer
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self._fallback_extractor = StructuredPydanticGraphExtractor()
        self._default_kb_id = uuid4()

    def _build_system_prompt(
        self, ontology: OntologySchema, known_entities: list[CanonicalEntity]
    ) -> str:
        prompt_lines = [
            "Você é um extrator ontológico especializado em construir Knowledge Graphs precisos.",
            f"Nome da Ontologia: {ontology.name}",
            f"Descrição: {ontology.description or 'Sem descrição'}",
            "",
            "--- TIPOS DE NÓS PERMITIDOS ---",
        ]
        for nt in ontology.node_types:
            props = ", ".join(f"{p.name} ({p.type.value})" for p in nt.properties)
            prompt_lines.append(f"- {nt.name}: {nt.description or ''} [Props: {props}]")

        prompt_lines.append("\n--- TIPOS DE RELAÇÕES PERMITIDAS ---")
        for rt in ontology.relationship_types:
            desc = rt.description or ""
            prompt_lines.append(
                f"- ({rt.source_node_type}) -[{rt.name}]-> ({rt.target_node_type}): {desc}"
            )

        if known_entities:
            prompt_lines.append("\n--- CATÁLOGO DE ENTIDADES CONHECIDAS ---")
            prompt_lines.append(
                "ATENÇÃO: Se o texto mencionar entidade equivalente ou sinônimo de uma entidade "
                "conhecida abaixo, REUTILIZE o mesmo 'id' e 'name' canônico!"
            )
            for e in known_entities[:100]:  # Limite de segurança de contexto
                aliases_str = f" (Aliases: {', '.join(e.aliases)})" if e.aliases else ""
                prompt_lines.append(
                    f"* ID: '{e.id}' | Tipo: '{e.entity_type}' | Nome: '{e.name}'{aliases_str}"
                )
        else:
            prompt_lines.append(
                "\nPara entidades inéditas, crie um 'id' normalizado (ex: 'org_stf', 'art_5')."
            )

        return "\n".join(prompt_lines)

    async def extract_graph(
        self,
        markdown_text: str,
        ontology: OntologySchema,
        kb_id: UUID | None = None,
    ) -> ExtractedGraph:
        if not self._api_key:
            # Fallback determinístico para testes e ambientes sem API key
            fallback_res = await self._fallback_extractor.extract_graph(markdown_text, ontology)
            # Registra entidades do fallback no catálogo
            target_kb = kb_id or self._default_kb_id
            for node in fallback_res.nodes:
                await self._registry.register_entity(
                    target_kb,
                    CanonicalEntity(
                        id=node.id,
                        name=node.properties.get("name", node.id),
                        entity_type=node.node_type,
                        aliases=[node.id],
                    ),
                )
            return fallback_res

        target_kb = kb_id or self._default_kb_id
        known_entities = await self._registry.get_all_distinct(target_kb)
        system_prompt = self._build_system_prompt(ontology, known_entities)

        async with self._semaphore:
            if self._provider_type == "openrouter":
                openrouter_model: OpenAIResponsesModel = (
                    PydanticAiOpenRouterProviderFactory.create_model(
                        api_key=self._api_key,
                        model_name=self._model_name,
                        base_url=self._base_url,
                        app_title=self._app_title,
                        app_referer=self._app_referer,
                        rate_limiter=self._limiter,
                    )
                )
                agent: Agent[None, _GraphExtractionOutput] = Agent(
                    model=openrouter_model,
                    system_prompt=system_prompt,
                    output_type=_GraphExtractionOutput,
                )
            else:
                transport = RateLimitedAsyncTransport(rate_limiter=self._limiter)
                async with httpx.AsyncClient(transport=transport, timeout=60.0) as http_client:
                    google_provider = GoogleProvider(api_key=self._api_key, http_client=http_client)
                    google_model = GoogleModel(self._model_name, provider=google_provider)
                    agent = Agent(
                        model=google_model,
                        system_prompt=system_prompt,
                        output_type=_GraphExtractionOutput,
                    )

            user_prompt = (
                "Extraia todos os nós e relações do seguinte fragmento "
                f"respeitando a ontologia:\n\n```markdown\n{markdown_text}\n```"
            )

            try:
                run_result = await agent.run(user_prompt)
                output: _GraphExtractionOutput = run_result.output
            except Exception:
                # Fallback resiliente para extração estruturada se o provedor remoto falhar
                fallback_res = await self._fallback_extractor.extract_graph(markdown_text, ontology)
                for node in fallback_res.nodes:
                    await self._registry.register_entity(
                        target_kb,
                        CanonicalEntity(
                            id=node.id,
                            name=node.properties.get("name", node.id),
                            entity_type=node.node_type,
                            aliases=[node.id],
                        ),
                    )
                return fallback_res

            nodes: list[GraphNode] = []
            edges: list[GraphEdge] = []

            for ent in output.entities:
                # Registra no catálogo cumulativo
                await self._registry.register_entity(
                    target_kb,
                    CanonicalEntity(
                        id=ent.id,
                        name=ent.name,
                        entity_type=ent.entity_type,
                        aliases=ent.aliases,
                    ),
                )
                props = dict(ent.properties)
                props["name"] = ent.name
                nodes.append(
                    GraphNode(
                        id=ent.id,
                        node_type=ent.entity_type,
                        properties=props,
                    )
                )

            for rel in output.relations:
                edges.append(
                    GraphEdge(
                        source_id=rel.source_id,
                        target_id=rel.target_id,
                        relationship_type=rel.relationship_type,
                        properties=rel.properties,
                    )
                )

            return ExtractedGraph(nodes=nodes, edges=edges)
