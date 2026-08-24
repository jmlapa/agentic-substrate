from src.modules.knowledge.infrastructure.adapters.audio_transcription_formatter import (
    AudioTranscriptionFormatter,
)


def test_format_empty_segments() -> None:
    formatter = AudioTranscriptionFormatter()
    md = formatter.format_to_markdown(
        file_name="voice.m4a",
        segments=[],
        ingested_at=1787238000.0,
    )
    assert "# Transcrição de Áudio: voice.m4a" in md
    assert "Nenhum áudio inteligível detectado." in md


def test_format_single_segment() -> None:
    formatter = AudioTranscriptionFormatter()
    segments = [
        {"start": 0.0, "end": 5.2, "text": "Olá mundo, este é um teste de gravação de voz."}
    ]
    md = formatter.format_to_markdown(
        file_name="nota.ogg",
        segments=segments,
        ingested_at=1787238000.0,
    )
    assert "# Transcrição de Áudio: nota.ogg" in md
    assert "## [00:00 - 00:05]" in md
    assert "Olá mundo, este é um teste de gravação de voz." in md


def test_format_grouping_multi_segments() -> None:
    formatter = AudioTranscriptionFormatter(max_block_seconds=120)
    segments = [
        {"start": 0.0, "end": 30.0, "text": "Primeira parte da reunião."},
        {"start": 30.5, "end": 75.0, "text": "Segunda parte continuando a mesma ideia."},
        {"start": 130.0, "end": 150.0, "text": "Novo bloco temporal que passou dos 120s."},
    ]
    md = formatter.format_to_markdown(
        file_name="reuniao.mp3",
        segments=segments,
        ingested_at=1787238000.0,
    )
    assert "## [00:00 - 01:15]" in md
    assert "Primeira parte da reunião. Segunda parte continuando a mesma ideia." in md
    assert "## [02:10 - 02:30]" in md
    assert "Novo bloco temporal que passou dos 120s." in md
