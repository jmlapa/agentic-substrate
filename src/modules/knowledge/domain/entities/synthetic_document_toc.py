from pydantic import BaseModel, Field

from src.modules.knowledge.domain.value_objects.hierarchical_toc_item import (
    HierarchicalTocItem,
)


class SyntheticDocumentToc(BaseModel):
    """
    Entidade de domínio representando a árvore de sumário sintético do documento completo.
    Fornece consultas determinísticas de linhagem hierárquica ativa para cada página individual.
    """

    items: list[HierarchicalTocItem] = Field(
        default_factory=list,
        description="Lista ordenada cronologicamente de nós estruturais do documento",
    )

    @property
    def total_headings(self) -> int:
        return len(self.items)

    @property
    def document_title(self) -> str | None:
        for item in self.items:
            if item.type == "document_title" or item.markdown_level == "#":
                return item.title
        return None

    def get_active_hierarchy_for_page(self, page_number: int) -> str:
        """
        Calcula e retorna a linhagem de cabeçalhos ativos até a página especificada.
        Se a página não tiver novos cabeçalhos, retorna o último estado ativo
        das páginas anteriores.
        """
        # Filtra itens até a página alvo
        past_or_current = [item for item in self.items if item.page <= page_number]
        if not past_or_current:
            return "Início do documento (nenhuma seção anterior aberta)."

        active_h1 = self.document_title
        active_h2: str | None = None
        active_h3: str | None = None
        active_h4: str | None = None

        for item in past_or_current:
            if item.markdown_level == "#":
                active_h1 = item.title
            elif item.markdown_level == "##":
                active_h2 = item.title
                active_h3 = None
                active_h4 = None
            elif item.markdown_level == "###":
                active_h3 = item.title
                active_h4 = None
            elif item.markdown_level == "####":
                active_h4 = item.title

        lineage_parts: list[str] = []
        if active_h1:
            lineage_parts.append(f"# {active_h1}")
        if active_h2:
            lineage_parts.append(f"## {active_h2}")
        if active_h3:
            lineage_parts.append(f"### {active_h3}")
        if active_h4:
            lineage_parts.append(f"#### {active_h4}")

        return " -> ".join(lineage_parts) if lineage_parts else "Documento Geral"

    def to_markdown_toc(self) -> str:
        """Renderiza o sumário sintético em formato de lista Markdown navegável."""
        lines = ["# Índice / Table of Contents\n"]
        for item in self.items:
            indent = ""
            if item.markdown_level == "##":
                indent = "- "
            elif item.markdown_level == "###":
                indent = "  - "
            elif item.markdown_level == "####":
                indent = "    - "
            else:
                continue  # Skip root # in bullet list

            lines.append(f"{indent}[{item.title}](#pág-{item.page})")

        return "\n".join(lines)
