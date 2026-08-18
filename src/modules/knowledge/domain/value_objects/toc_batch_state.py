from pydantic import BaseModel, ConfigDict, Field


class TocBatchState(BaseModel):
    """
    Value Object imutável representando o estado hierárquico transportado
    entre lotes de páginas consecutivos no Stateful Rolling Window ToC.
    """

    model_config = ConfigDict(frozen=True)

    active_section: str | None = Field(
        default=None, description="Última seção principal ativa (##)"
    )
    active_subsection: str | None = Field(default=None, description="Última subseção ativa (###)")
    active_markdown_level: str | None = Field(
        default=None, description="Último nível markdown ativo (#, ##, ###, ####)"
    )
    last_page_processed: int = Field(
        default=0, ge=0, description="Número da última página processada no lote anterior"
    )

    @classmethod
    def initial(cls) -> "TocBatchState":
        """Cria o estado inicial para o primeiro lote de páginas."""
        return cls(
            active_section=None,
            active_subsection=None,
            active_markdown_level=None,
            last_page_processed=0,
        )

    def to_prompt_context(self) -> str:
        """Formata o estado para injeção no prompt do próximo lote."""
        if self.last_page_processed == 0:
            return "Estado prévio: Início do documento (nenhuma seção anterior aberta)."

        sec = self.active_section or "Nenhuma"
        subsec = self.active_subsection or "Nenhuma"
        lvl = self.active_markdown_level or "Nenhum"

        return (
            f"Estado hierárquico herdado da Página {self.last_page_processed}:\n"
            f"- Seção Principal Ativa (##): {sec}\n"
            f"- Subseção Ativa (###): {subsec}\n"
            f"- Nível Ativo: {lvl}\n"
            f"Subseções não nomeadas continuam sob a seção/subseção ativa acima."
        )
