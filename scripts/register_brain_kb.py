"""
Script para registrar a Ontologia de Squads de Produto e Engenharia de Software
e recriar a Knowledge Base do Brain com documentação fundamental.
"""

import asyncio
from typing import Any

import httpx

from src.api_gateway.main import app
from src.modules.knowledge.domain.ontology import (
    ProductSoftwareSquadOntologyFactory,
)

BASE_URL = "http://localhost:8000"


async def get_client() -> httpx.AsyncClient:
    try:
        client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        resp = await client.get("/health")
        if resp.status_code == 200:
            return client
    except Exception:
        pass
    # Fallback in-process ASGI se o container externo não responder
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=30.0)


async def register_ontology(client: httpx.AsyncClient) -> str:
    print("=================================================================")
    print("📐  Verificando / Registrando 'ProductSoftwareSquadOntology'...")
    print("=================================================================")

    # 1. Verificar se já existe
    list_resp = await client.get("/api/v1/ontologies")
    if list_resp.status_code == 200:
        templates = list_resp.json().get("templates", [])
        for t in templates:
            if t["name"] == ProductSoftwareSquadOntologyFactory.ONTOLOGY_NAME:
                print(f"✔ Ontologia já existente encontrada com ID: {t['id']}")
                return str(t["id"])

    # 2. Criar via Factory
    schema = ProductSoftwareSquadOntologyFactory.create_schema()
    payload = {
        "name": schema.name,
        "description": schema.description,
        "version": 1,
        "node_types": [n.model_dump() for n in schema.node_types],
        "relationship_types": [r.model_dump() for r in schema.relationship_types],
    }

    create_resp = await client.post("/api/v1/ontologies", json=payload)
    if create_resp.status_code == 201:
        data = create_resp.json()
        print("✔ Ontologia registrada com sucesso!")
        print(f"ID da Ontologia: {data['id']}")
        print(f"Nome: {data['name']} (v{data['version']})")
        print(f"Nós ({len(data['node_types'])}): {[n['name'] for n in data['node_types']]}")
        print(
            f"Relações ({len(data['relationship_types'])}): "
            f"{[r['name'] for r in data['relationship_types']]}"
        )
        return str(data["id"])
    else:
        raise RuntimeError(
            f"Erro ao registrar ontologia (Status {create_resp.status_code}): {create_resp.text}"
        )


async def create_brain_kb(client: httpx.AsyncClient, ontology_id: str) -> dict[str, Any]:
    print("\n=================================================================")
    print("🧠  Verificando / Criando Knowledge Base 'Brain'...")
    print("=================================================================")

    # 1. Verificar se já existe
    list_resp = await client.get("/api/v1/knowledge/bases")
    if list_resp.status_code == 200:
        kbs = list_resp.json().get("knowledge_bases", [])
        for kb in kbs:
            if kb["name"] == "Brain":
                print(f"✔ Knowledge Base 'Brain' já existe! ID: {kb['id']}")
                return dict(kb)

    # 2. Criar nova KB
    kb_payload = {
        "name": "Brain",
        "description": (
            "Base de conhecimento unificada do Squad Brain — cobrindo iniciativas de "
            "Applied AI Products (como Conversational Commerce), Explore AI e "
            "Substrate (plataformização de IA), com governança de produtos, "
            "arquitetura de software, ADRs e catálogo de IA."
        ),
        "ontology_id": ontology_id,
    }

    resp = await client.post("/api/v1/knowledge/bases", json=kb_payload)
    if resp.status_code == 201:
        kb_data = resp.json()
        print("✔ Knowledge Base 'Brain' criada com sucesso!")
        print(f"ID da KB: {kb_data['id']}")
        print(f"Nome: {kb_data['name']}")
        print(f"Partição de Storage: {kb_data['storage_partition']}")
        return dict(kb_data)
    else:
        raise RuntimeError(
            f"Erro ao criar Knowledge Base 'Brain' (Status {resp.status_code}): {resp.text}"
        )


async def upload_foundational_doc(client: httpx.AsyncClient, kb_id: str) -> None:
    print("\n=================================================================")
    print("📄  Carregando Documento Fundamental do Squad Brain...")
    print("=================================================================")

    doc_content = """# Squad Brain: Visão Geral, Iniciativas e Arquitetura

O **Squad Brain** é a unidade de engenharia e produto focada em Inteligência Artificial, responsável por transformar capacidades de IA em produtos de alto impacto, explorar novas fronteiras tecnológicas e construir a infraestrutura compartilhada (plataformização).

---

## 1. Organização e Iniciativas Estratégicas

O Squad Brain estrutura suas operações em torno de 3 linhas de iniciativas estratégicas:

### 1.1 Applied AI Products
Desenvolvimento de produtos finais orientados a valor imediato de negócio e interação com usuários.
- **Produto Principal:** *Conversational Commerce*
- **Proposta de Valor:** Transformar a experiência de compra por meio de agentes conversacionais inteligentes com recomendação em tempo real, catálogo semântico e checkout guiado.
- **Agentes:**
  - *Sales Advisor Agent:* Especialista consultivo para recomendação de produtos com base no perfil do consumidor.
  - *Support Agent:* Resolução de dúvidas de pedidos, rastreamento e políticas de pós-venda.
- **Métricas Chave:** Taxa de Conversão Conversacional, Ticket Médio, Resolução em Primeiro Contato (FCR).

### 1.2 Explore AI
Iniciativas de pesquisa aplicada, experimentação rápida e validação de hipóteses com tecnologias emergentes de IA.
- **Escopo:**
  - Protótipos de agentes multimodais e assistentes de voz em baixa latência.
  - Avaliação contínua de novos modelos de fundação (benchmarks de raciocínio, acurácia e custo).
  - Exploração de novas abordagens de RAG estruturado, grafos de conhecimento dinâmicos e memória de longo prazo.

### 1.3 Substrate (Plataformização de IA)
A espinha dorsal de infraestrutura e engenharia que alimenta todos os produtos e explorações do Brain.
- **Sistema:** *Agentic Substrate*
- **Componentes Principais:**
  - *Ingestion Engine:* Motor distribuído de ingestão massiva e concorrente de documentos com suporte multimodal.
  - *FalkorDB Graph Store Adapter:* Persistência em grafo de conhecimento em alta performance via Cypher UNWIND batching.
  - *Redis Stream Job Queue:* Mensageria distribuída com semântica At-Least-Once e controle de barreira atômica.
  - *Document Aggregate:* Aggregate Root soberano para replay O(1) de eventos sem contenção de concorrência.
- **Decisões Arquiteturais (ADRs):**
  - *ADR-001:* Decomposição DDD em DocumentAggregate soberano eliminando version locks no PostgreSQL.
  - *ADR-002:* Adoção de Redis Streams e Atomic Job Barrier para coordenação de chunks de OCR e Grafo.
  - *ADR-003:* Cypher UNWIND Batching e ThreadPool dedicado de 64 workers no FalkorDB.
- **Tecnologias:** Python, FastAPI, PostgreSQL (com pgvector), FalkorDB, Redis, LiteLLM / OpenRouter.
- **Modelos Utilizados:** Claude 3.5 Sonnet, Qwen 2.5 72B, Gemini 1.5 Pro, Whisper.
- **Mitigação de Riscos:**
  - *Risco de Concorrência:* Mitigado pelo isolamento em streams curtos unitários doc-{id}.
  - *Risco de Token Loss:* Mitigado por checkpoints duráveis em disco a cada página/chunk.

---

## 2. Governança e Métricas do Squad
- **Métricas Técnicas:** Latência P95 < 2s, Custo médio de tokens por sessão, Disponibilidade 99.9%.
- **Métricas de Produto:** CSAT > 90%, Engajamento de usuários em fluxos de IA conversacional.
"""

    files = {
        "file": (
            "brain_squad_overview.md",
            doc_content.encode("utf-8"),
            "text/markdown",
        )
    }

    resp = await client.post(
        f"/api/v1/knowledge/bases/{kb_id}/documents",
        files=files,
    )

    if resp.status_code in (200, 202):
        print("✔ Documento fundamental anexado com sucesso!")
        print(f"Resposta: {resp.json()}")
    else:
        print(f"⚠️  Aviso ao anexar documento (Status {resp.status_code}): {resp.text}")


async def main() -> None:
    client = await get_client()
    try:
        ontology_id = await register_ontology(client)
        kb_info = await create_brain_kb(client, ontology_id)
        await upload_foundational_doc(client, kb_info["id"])
        print("\n=================================================================")
        print("✨ Concluído com sucesso! Knowledge Base do Brain está ativa e pronta.")
        print("=================================================================")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
