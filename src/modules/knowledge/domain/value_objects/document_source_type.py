from enum import StrEnum
from pathlib import Path


class DocumentSourceType(StrEnum):
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"

    @classmethod
    def infer(cls, file_name: str, content_type: str | None = None) -> "DocumentSourceType":
        if content_type:
            ct = content_type.lower().strip()
            if ct.startswith("image/"):
                return cls.IMAGE
            if ct.startswith("audio/") or ct == "video/3gpp":
                return cls.AUDIO
            if ct.startswith("text/") or ct in (
                "application/pdf",
                "application/json",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/x-subrip",
            ):
                return cls.DOCUMENT

        ext = Path(file_name).suffix.lower()

        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"}
        if ext in image_extensions:
            return cls.IMAGE

        audio_extensions = {
            ".mp3",
            ".m4a",
            ".ogg",
            ".opus",
            ".oga",
            ".webm",
            ".wav",
            ".aac",
            ".caf",
            ".amr",
            ".3gp",
        }
        if ext in audio_extensions:
            return cls.AUDIO

        return cls.DOCUMENT
