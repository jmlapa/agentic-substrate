from datetime import UTC, datetime
from typing import Any


class AudioTranscriptionFormatter:
    """
    Formatador algorítmico puro que converte segmentos temporais de transcrição
    (como os emitidos pelo Whisper em verbose_json) em Markdown hierárquico
    com seções temporais bem delimitadas para processamento por Parent-Child Chunkers.
    """

    def __init__(self, max_block_seconds: int = 120) -> None:
        self._max_block_seconds = max_block_seconds

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        total_seconds = max(0, int(seconds))
        minutes = total_seconds // 60
        secs = total_seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def format_to_markdown(
        self,
        file_name: str,
        segments: list[dict[str, Any]],
        ingested_at: float | None = None,
    ) -> str:
        lines: list[str] = [f"# Transcrição de Áudio: {file_name}"]

        dt_str = "N/A"
        if ingested_at is not None:
            dt = datetime.fromtimestamp(ingested_at, tz=UTC)
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        lines.append(f"*Data de Ingestão: {dt_str}*")
        lines.append("")

        if not segments:
            lines.append("Nenhum áudio inteligível detectado.")
            return "\n".join(lines)

        blocks: list[tuple[float, float, list[str]]] = []
        current_start = float(segments[0].get("start", 0.0))
        current_end = float(segments[0].get("end", 0.0))
        current_texts: list[str] = []

        for seg in segments:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))
            text = str(seg.get("text", "")).strip()

            if not text:
                continue

            if not current_texts:
                current_start = start
                current_end = end
                current_texts.append(text)
                continue

            if (end - current_start > self._max_block_seconds) or (start - current_end > 10.0):
                blocks.append((current_start, current_end, current_texts))
                current_start = start
                current_end = end
                current_texts = [text]
            else:
                current_end = end
                current_texts.append(text)

        if current_texts:
            blocks.append((current_start, current_end, current_texts))

        for b_start, b_end, texts in blocks:
            start_str = self._format_seconds(b_start)
            end_str = self._format_seconds(b_end)
            lines.append(f"## [{start_str} - {end_str}]")
            lines.append(" ".join(texts))
            lines.append("")

        return "\n".join(lines).strip()
