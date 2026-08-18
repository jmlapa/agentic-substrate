from src.modules.knowledge.domain.value_objects.toc_batch_state import TocBatchState


def test_create_initial_toc_batch_state() -> None:
    state = TocBatchState.initial()
    assert state.active_section is None
    assert state.active_subsection is None
    assert state.active_markdown_level is None
    assert state.last_page_processed == 0


def test_toc_batch_state_context_formatting() -> None:
    state = TocBatchState(
        active_section="2. Methods",
        active_subsection="2.1 Literature Search",
        active_markdown_level="###",
        last_page_processed=25,
    )
    context_str = state.to_prompt_context()
    assert "2. Methods" in context_str
    assert "2.1 Literature Search" in context_str
    assert "###" in context_str
    assert "25" in context_str


def test_toc_batch_state_initial_prompt_context() -> None:
    state = TocBatchState.initial()
    context_str = state.to_prompt_context()
    assert "Início do documento" in context_str
