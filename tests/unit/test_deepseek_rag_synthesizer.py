import pytest

from src.modules.knowledge.infrastructure.adapters.deepseek_rag_synthesizer import (
    DeepSeekRagSynthesizer,
)
from src.modules.knowledge.infrastructure.adapters.openrouter_rag_synthesizer import (
    OpenRouterRagSynthesizer,
)


def test_deepseek_rag_synthesizer_alias_compatibility() -> None:
    assert issubclass(DeepSeekRagSynthesizer, OpenRouterRagSynthesizer)
    assert DeepSeekRagSynthesizer is OpenRouterRagSynthesizer


@pytest.mark.asyncio
async def test_deepseek_alias_empty_results() -> None:
    synth = DeepSeekRagSynthesizer(api_key="test")
    res = await synth.synthesize_answer("teste", [])
    assert "Nenhum documento" in res
