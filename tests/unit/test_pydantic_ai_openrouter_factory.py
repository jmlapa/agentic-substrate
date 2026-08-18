from pydantic_ai.models.openai import OpenAIResponsesModel

from src.kernel.infrastructure.async_token_bucket_limiter import AsyncTokenBucketLimiter
from src.modules.knowledge.infrastructure.adapters.pydantic_ai_openrouter_provider_factory import (
    PydanticAiOpenRouterProviderFactory,
)


def test_pydantic_ai_openrouter_factory_creates_openai_responses_model() -> None:
    limiter = AsyncTokenBucketLimiter(max_rpm=200)
    model = PydanticAiOpenRouterProviderFactory.create_model(
        api_key="sk-or-test-key",
        model_name="deepseek/deepseek-v4-flash",
        base_url="https://openrouter.ai/api/v1",
        app_title="Agentic Substrate Test",
        app_referer="https://test.local",
        rate_limiter=limiter,
    )

    assert isinstance(model, OpenAIResponsesModel)
    assert model.model_name == "deepseek/deepseek-v4-flash"
    assert model.provider is not None
    # Inspect internal custom client
    custom_client = getattr(model.provider, "_client", None)
    assert custom_client is not None
    assert str(custom_client.base_url) == "https://openrouter.ai/api/v1/"
    assert custom_client.api_key == "sk-or-test-key"
    assert custom_client.default_headers.get("HTTP-Referer") == "https://test.local"
    assert custom_client.default_headers.get("X-Title") == "Agentic Substrate Test"
