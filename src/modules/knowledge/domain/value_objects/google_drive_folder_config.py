from pydantic import Field, field_validator

from src.kernel.domain.value_object import ValueObject


class GoogleDriveFolderConfig(ValueObject):
    folder_id: str
    recursive: bool = True
    baseline_days: int = 30
    include_mime_types: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.google-apps.document",
            "application/vnd.google-apps.spreadsheet",
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
        return cleaned

    @field_validator("baseline_days")
    @classmethod
    def validate_baseline_days(cls, v: int) -> int:
        if v < 0:
            raise ValueError("baseline_days must be non-negative")
        return v
