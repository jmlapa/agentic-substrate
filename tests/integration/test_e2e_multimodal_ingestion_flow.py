import io
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from src.api_gateway.container import create_app_container
from src.api_gateway.main import create_app


@pytest.mark.asyncio
async def test_e2e_multimodal_ingestion_and_query_flow() -> None:
    test_container = create_app_container(run_in_background=False)
    test_app = create_app(container=test_container)
    transport = ASGITransport(app=test_app)

    mock_vlm_response = {
        "choices": [{"message": {"content": "# Diagrama\n\nAuthGateway autentica tokens JWT."}}]
    }

    mock_whisper_response = {
        "text": "Retenção de logs será de 90 dias em armazenamento frio.",
        "segments": [
            {
                "start": 0.0,
                "end": 5.2,
                "text": "Retenção de logs será de 90 dias em armazenamento frio.",
            }
        ],
    }

    img = Image.new("RGB", (100, 100), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    png_bytes = img_byte_arr.getvalue()

    fake_mp3_bytes = b"ID3\x03\x00\x00\x00\x00\x00#FakeMp3DataPayload12345"

    original_post = httpx.AsyncClient.post

    async def fake_post(self_client: httpx.AsyncClient, url: Any, *args: Any, **kwargs: Any) -> Any:
        url_str = str(url)
        if "openrouter.ai" in url_str:
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.raise_for_status = MagicMock()
            if "transcriptions" in url_str:
                mock_res.json.return_value = mock_whisper_response
            else:
                mock_res.json.return_value = mock_vlm_response
            return mock_res
        return await original_post(self_client, url, *args, **kwargs)

    with patch("httpx.AsyncClient.post", new=fake_post):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ont_payload = {
                "name": "ArchitectureOntology",
                "description": "Ontologia para sistemas",
                "node_types": [
                    {
                        "name": "Component",
                        "description": "Componente do sistema",
                        "properties": [{"name": "name", "type": "string", "required": True}],
                    }
                ],
                "relationship_types": [],
                "version": 1,
            }
            ont_resp = await client.post("/api/v1/ontologies", json=ont_payload)
            assert ont_resp.status_code == 201
            ont_id = ont_resp.json()["id"]

            kb_resp = await client.post(
                "/api/v1/knowledge/bases",
                json={
                    "name": "Multimodal Brain",
                    "description": "KB com doc, image e audio",
                    "ontology_id": ont_id,
                },
            )
            assert kb_resp.status_code == 201
            kb_id = kb_resp.json()["id"]

            # A) Documento Markdown
            doc_file = {
                "file": (
                    "system_specs.md",
                    b"# Especificacao\n\nCoreEngine processa transacoes com sub-milisegundo.",
                    "text/markdown",
                )
            }
            res_doc = await client.post(
                f"/api/v1/knowledge/bases/{kb_id}/documents", files=doc_file
            )
            assert res_doc.status_code == 202
            doc_id = res_doc.json()["document_id"]

            # B) Imagem PNG (VLM OCR)
            img_file = {
                "file": (
                    "infra_diagram.png",
                    png_bytes,
                    "image/png",
                )
            }
            res_img = await client.post(
                f"/api/v1/knowledge/bases/{kb_id}/documents",
                files=img_file,
                data={"enable_ocr": True, "ocr_instructions": "Transcreva o diagrama de blocos"},
            )
            assert res_img.status_code == 202
            img_id = res_img.json()["document_id"]

            # C) Áudio MP3 (Whisper Transcription)
            audio_file = {
                "file": (
                    "meeting_recording.mp3",
                    fake_mp3_bytes,
                    "audio/mpeg",
                )
            }
            res_audio = await client.post(
                f"/api/v1/knowledge/bases/{kb_id}/documents", files=audio_file
            )
            assert res_audio.status_code == 202
            audio_id = res_audio.json()["document_id"]

            # Verificação na Knowledge Base
            kb_get = await client.get(f"/api/v1/knowledge/bases/{kb_id}")
            assert kb_get.status_code == 200
            kb_data = kb_get.json()
            docs_in_kb = {d["id"]: d for d in kb_data["documents"]}

            assert doc_id in docs_in_kb
            assert img_id in docs_in_kb
            assert audio_id in docs_in_kb

            assert docs_in_kb[doc_id]["file_name"] == "system_specs.md"
            assert docs_in_kb[img_id]["file_name"] == "infra_diagram.png"
            assert docs_in_kb[audio_id]["file_name"] == "meeting_recording.mp3"

            # Query 1: ÁUDIO
            q_audio = await client.post(
                f"/api/v1/knowledge/bases/{kb_id}/query",
                json={
                    "query": "qual e o tempo de retencao de logs?",
                    "top_k": 5,
                    "mode": "retrieve",
                    "source_types": ["audio"],
                },
            )
            assert q_audio.status_code == 200
            data_audio = q_audio.json()
            assert data_audio["retrieval_trace"]["source_types"] == ["audio"]
            assert len(data_audio["results"]) >= 1
            for r in data_audio["results"]:
                assert r["source_type"] == "audio"
                assert r["document_name"] == "meeting_recording.mp3"
                assert "90 dias" in r["parent_content"]

            # Query 2: IMAGEM
            q_img = await client.post(
                f"/api/v1/knowledge/bases/{kb_id}/query",
                json={
                    "query": "como funciona o AuthGateway?",
                    "top_k": 5,
                    "mode": "retrieve",
                    "source_types": ["image"],
                },
            )
            assert q_img.status_code == 200
            data_img = q_img.json()
            assert data_img["retrieval_trace"]["source_types"] == ["image"]
            assert len(data_img["results"]) >= 1
            for r in data_img["results"]:
                assert r["source_type"] == "image"
                assert r["document_name"] == "infra_diagram.png"
                assert "AuthGateway" in r["parent_content"]

            # Query 3: DOCUMENTO
            q_doc = await client.post(
                f"/api/v1/knowledge/bases/{kb_id}/query",
                json={
                    "query": "qual o desempenho do CoreEngine?",
                    "top_k": 5,
                    "mode": "retrieve",
                    "source_types": ["document"],
                },
            )
            assert q_doc.status_code == 200
            data_doc = q_doc.json()
            assert data_doc["retrieval_trace"]["source_types"] == ["document"]
            assert len(data_doc["results"]) >= 1
            for r in data_doc["results"]:
                assert r["source_type"] == "document"
                assert r["document_name"] == "system_specs.md"
                assert "CoreEngine" in r["parent_content"]

            # Query 4: Geral (todas as 3 origens recuperadas)
            q_all = await client.post(
                f"/api/v1/knowledge/bases/{kb_id}/query",
                json={
                    "query": "informações do sistema",
                    "top_k": 10,
                    "mode": "retrieve",
                },
            )
            assert q_all.status_code == 200
            data_all = q_all.json()
            assert len(data_all["results"]) == 3
            types_found = {r["source_type"] for r in data_all["results"]}
            assert types_found == {"document", "image", "audio"}
