"""
Script para registrar a Ontologia Jurídica Brasileira Universal via API REST.
"""

import asyncio

import httpx

from src.api_gateway.main import app

LEGAL_ONTOLOGY_PAYLOAD = {
    "name": "OntologiaJuridicaBrasileira",
    "description": (
        "Ontologia universal para a legislação brasileira (CF/88, Leis Complementares, "
        "Leis Ordinárias, Códigos e Decretos), aderente à LC 95/98 e à Teoria Geral do Direito."
    ),
    "version": 1,
    "node_types": [
        {
            "name": "AtoNormativo",
            "description": "Espécie normativa brasileira (CF, Lei, Decreto, MPV)",
            "properties": [
                {"name": "sigla", "type": "string", "required": False},
                {"name": "tipo", "type": "string", "required": True},
                {"name": "numero", "type": "string", "required": False},
                {"name": "ano", "type": "integer", "required": False},
                {"name": "ementa", "type": "string", "required": False},
                {"name": "status", "type": "string", "required": False, "default": "Vigente"},
            ],
        },
        {
            "name": "Dispositivo",
            "description": "Artigo, Parágrafo ou Inciso conforme LC 95/98",
            "properties": [
                {"name": "rotulo", "type": "string", "required": True},
                {"name": "tipo", "type": "string", "required": True},
                {"name": "tema", "type": "string", "required": False},
            ],
        },
        {
            "name": "SujeitoDireito",
            "description": "Pessoa, órgão, ente estatal ou autoridade mencionada na lei",
            "properties": [
                {"name": "categoria", "type": "string", "required": True},
                {"name": "sigla", "type": "string", "required": False},
                {"name": "esfera_poder", "type": "string", "required": False},
            ],
        },
        {
            "name": "CompetenciaDever",
            "description": "Competência, dever funcional, obrigação ou vedação legal",
            "properties": [
                {"name": "tipo", "type": "string", "required": True},
                {"name": "descricao", "type": "string", "required": False},
            ],
        },
        {
            "name": "DireitoGarantia",
            "description": "Prerrogativa, direito subjetivo ou garantia fundamental",
            "properties": [
                {"name": "categoria", "type": "string", "required": True},
                {
                    "name": "remedio_constitucional",
                    "type": "boolean",
                    "required": False,
                    "default": False,
                },
            ],
        },
        {
            "name": "SancaoConsequencia",
            "description": "Penalidade, multa, tipo penal ou sanção por descumprimento",
            "properties": [
                {"name": "natureza", "type": "string", "required": True},
                {"name": "descricao", "type": "string", "required": False},
            ],
        },
        {
            "name": "InstitutoConceito",
            "description": "Definição legal, instituto jurídico ou princípio",
            "properties": [
                {"name": "tipo", "type": "string", "required": True},
                {"name": "descricao", "type": "string", "required": False},
            ],
        },
    ],
    "relationship_types": [
        {
            "name": "ESTRUTURADO_EM",
            "description": "Ato normativo é composto por seus respectivos dispositivos e artigos",
            "source_node_type": "AtoNormativo",
            "target_node_type": "Dispositivo",
        },
        {
            "name": "ESTABELECE_COMPETENCIA",
            "description": "Dispositivo estabelece uma competência, poder ou obrigação",
            "source_node_type": "Dispositivo",
            "target_node_type": "CompetenciaDever",
        },
        {
            "name": "ASSEGURA_DIREITO",
            "description": "Dispositivo assegura um direito, garantia ou liberdade",
            "source_node_type": "Dispositivo",
            "target_node_type": "DireitoGarantia",
        },
        {
            "name": "PREVE_SANCAO",
            "description": "Dispositivo prevê sanção, pena, multa ou nulidade",
            "source_node_type": "Dispositivo",
            "target_node_type": "SancaoConsequencia",
        },
        {
            "name": "DEFINE_INSTITUTO",
            "description": "Dispositivo conceitua ou regulamenta instituto jurídico ou princípio",
            "source_node_type": "Dispositivo",
            "target_node_type": "InstitutoConceito",
        },
        {
            "name": "ATRIBUIDO_A",
            "description": "Competência ou dever atribuído a um sujeito, órgão ou autoridade",
            "source_node_type": "CompetenciaDever",
            "target_node_type": "SujeitoDireito",
        },
        {
            "name": "TITULARIZADO_POR",
            "description": "Direito garantido a um sujeito de direito (ex: cidadão, réu)",
            "source_node_type": "DireitoGarantia",
            "target_node_type": "SujeitoDireito",
        },
        {
            "name": "APLICA_SE_A",
            "description": "Sanção ou consequência punitiva aplicável a um sujeito de direito",
            "source_node_type": "SancaoConsequencia",
            "target_node_type": "SujeitoDireito",
        },
        {
            "name": "EXIGE_AUTORIZACAO_DE",
            "description": "Exercício da competência exige autorização de outro órgão ou poder",
            "source_node_type": "CompetenciaDever",
            "target_node_type": "SujeitoDireito",
        },
        {
            "name": "ALTERA_OU_REVOGA",
            "description": "Ato normativo altera ou revoga outro ato normativo ou dispositivo",
            "source_node_type": "AtoNormativo",
            "target_node_type": "AtoNormativo",
        },
        {
            "name": "REMISSIVA_A",
            "description": "Dispositivo faz remissão expressa a outro dispositivo ou ato",
            "source_node_type": "Dispositivo",
            "target_node_type": "Dispositivo",
        },
    ],
}


async def main() -> None:
    print("=================================================================")
    print("🏛️  Registrando 'OntologiaJuridicaBrasileira' via API REST...")
    print("=================================================================")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        resp = await client.post("/api/v1/ontologies", json=LEGAL_ONTOLOGY_PAYLOAD)
        if resp.status_code == 201:
            data = resp.json()
            print("✔ Registrado com sucesso via API Controller!")
            print(f"ID da Ontologia: {data['id']}")
            print(f"Nome: {data['name']} (v{data['version']})")
            print(f"Nós ({len(data['node_types'])}): {[n['name'] for n in data['node_types']]}")
            print(
                f"Relações ({len(data['relationship_types'])}): "
                f"{[r['name'] for r in data['relationship_types']]}"
            )
        else:
            print(f"❌ Erro ao registrar ontologia (Status {resp.status_code}): {resp.text}")


if __name__ == "__main__":
    asyncio.run(main())
