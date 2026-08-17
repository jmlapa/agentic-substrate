"""
CLI para Ingestão e Consulta na Base de Conhecimento Constitucional.
"""

import asyncio
import sys
from pathlib import Path

import httpx

from scripts.register_legal_ontology import LEGAL_ONTOLOGY_PAYLOAD
from src.api_gateway.main import app


async def setup_and_ingest(file_path: str) -> None:
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Arquivo não encontrado: {file_path}")
        return

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://localhost:8000", timeout=None
    ) as client:
        # 1. Registra / Obtém a ontologia jurídica
        print("1️⃣ Registrando Ontologia Jurídica...")
        ont_res = await client.post("/api/v1/ontologies", json=LEGAL_ONTOLOGY_PAYLOAD)
        ont_id = ont_res.json()["id"]
        print(f"   ✔ Ontologia ID: {ont_id}")

        # 2. Cria a Base de Conhecimento
        print("2️⃣ Criando Base de Conhecimento...")
        kb_payload = {
            "name": "Constituição Federal 1988",
            "description": "Base de conhecimento jurídica da CF/88",
            "ontology_id": ont_id,
        }
        kb_res = await client.post("/api/v1/knowledge/bases", json=kb_payload)
        kb_data = kb_res.json()
        kb_id = kb_data["id"]
        print(f"   ✔ Knowledge Base criada! ID: {kb_id}")

        # 3. Envia o arquivo para a Saga de Ingestão
        print(f"3️⃣ Enviando arquivo '{path.name}' para ingestão e GraphRAG...")
        mime = "application/pdf" if path.suffix == ".pdf" else "text/markdown"
        with open(path, "rb") as f:
            files = {"file": (path.name, f, mime)}
            doc_res = await client.post(f"/api/v1/knowledge/bases/{kb_id}/documents", files=files)

        if doc_res.status_code == 202:
            doc_data = doc_res.json()
            print(f"   ✔ Documento recebido! Doc ID: {doc_data['document_id']}")
            print(f"\n🎉 Sucesso! KB_ID para consultas: {kb_id}")
        else:
            print(f"❌ Erro no upload (Status {doc_res.status_code}): {doc_res.text}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: uv run python scripts/ingest_document.py <caminho_do_arquivo.pdf_ou_md>")
    else:
        asyncio.run(setup_and_ingest(sys.argv[1]))
