import pytest

from src.modules.knowledge.domain.value_objects.document_source_type import DocumentSourceType


@pytest.mark.parametrize(
    ("file_name", "content_type", "expected"),
    [
        # Documentos
        ("notes.md", "text/markdown", DocumentSourceType.DOCUMENT),
        ("report.markdown", None, DocumentSourceType.DOCUMENT),
        ("plain.txt", "text/plain", DocumentSourceType.DOCUMENT),
        ("paper.pdf", "application/pdf", DocumentSourceType.DOCUMENT),
        (
            "spec.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            DocumentSourceType.DOCUMENT,
        ),
        (
            "slides.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            DocumentSourceType.DOCUMENT,
        ),
        (
            "data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            DocumentSourceType.DOCUMENT,
        ),
        ("table.csv", "text/csv", DocumentSourceType.DOCUMENT),
        ("article.html", "text/html", DocumentSourceType.DOCUMENT),
        ("payload.json", "application/json", DocumentSourceType.DOCUMENT),
        # Imagens
        ("screenshot.png", "image/png", DocumentSourceType.IMAGE),
        ("photo.jpg", "image/jpeg", DocumentSourceType.IMAGE),
        ("photo.jpeg", None, DocumentSourceType.IMAGE),
        ("sticker.webp", "image/webp", DocumentSourceType.IMAGE),
        ("camera.heic", "image/heic", DocumentSourceType.IMAGE),
        ("camera.heif", "image/heif", DocumentSourceType.IMAGE),
        # Áudios
        ("voice_memo.m4a", "audio/mp4", DocumentSourceType.AUDIO),
        ("podcast.mp3", "audio/mpeg", DocumentSourceType.AUDIO),
        ("whatsapp_voice.ogg", "audio/ogg", DocumentSourceType.AUDIO),
        ("whatsapp_voice.opus", "audio/opus", DocumentSourceType.AUDIO),
        ("telegram_voice.oga", "audio/ogg", DocumentSourceType.AUDIO),
        ("browser_record.webm", "audio/webm", DocumentSourceType.AUDIO),
        ("recording.wav", "audio/wav", DocumentSourceType.AUDIO),
        ("audio_track.aac", "audio/aac", DocumentSourceType.AUDIO),
        ("apple_dictation.caf", "audio/x-caf", DocumentSourceType.AUDIO),
        ("mobile_call.amr", "audio/amr", DocumentSourceType.AUDIO),
        ("mobile_call.3gp", "audio/3gpp", DocumentSourceType.AUDIO),
    ],
)
def test_document_source_type_inference(
    file_name: str, content_type: str | None, expected: DocumentSourceType
) -> None:
    assert DocumentSourceType.infer(file_name=file_name, content_type=content_type) == expected


def test_document_source_type_fallback_to_document() -> None:
    assert (
        DocumentSourceType.infer("unknown_file.xyz", "application/octet-stream")
        == DocumentSourceType.DOCUMENT
    )
    assert DocumentSourceType.infer("no_ext", None) == DocumentSourceType.DOCUMENT
