from enum import StrEnum


class AtomicBlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    TABLE = "table"
    LIST = "list"
    BLOCKQUOTE = "blockquote"
    THEMATIC_BREAK = "thematic_break"
