import re

from pydantic import ConfigDict, Field, field_validator

from src.kernel.domain.value_object import ValueObject

_DRIVE_FOLDER_ID_PATTERN = re.compile(r"^(root|[a-zA-Z0-9_-]+)$")


class GoogleDriveFolderConfig(ValueObject):
    model_config = ConfigDict(extra="forbid")

    folder_id: str
    recursive: bool = True
    baseline_days: int = 30
    include_mime_types: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.google-apps.document",
            "application/vnd.google-apps.spreadsheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "text/plain",
            "text/markdown",
            "audio/mpeg",
            "audio/wav",
            "audio/x-m4a",
        ]
    )

    @field_validator("folder_id")
    @classmethod
    def validate_folder_id(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("folder_id cannot be empty")
        if not _DRIVE_FOLDER_ID_PATTERN.match(cleaned):
            raise ValueError(
                "folder_id contains invalid characters (alphanumeric, hyphen, or underscore only)"
            )
        return cleaned

    @field_validator("baseline_days")
    @classmethod
    def validate_baseline_days(cls, v: int) -> int:
        if v < 0:
            raise ValueError("baseline_days must be non-negative")
        return v
