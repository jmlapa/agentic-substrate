from enum import StrEnum


class PropertyType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST_STRING = "list[string]"
