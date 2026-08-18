from typing import Any, cast

import httpx
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.kernel.infrastructure.async_token_bucket_limiter import (
    AsyncTokenBucketLimiter,
)
from src.kernel.infrastructure.rate_limited_async_transport import (
    RateLimitedAsyncTransport,
)


class PydanticAiOpenRouterProviderFactory:
    """
    Fábrica para instanciar OpenAIResponsesModel configurado para OpenRouter
    com cliente AsyncOpenAI customizado, headers de governança e controle de taxa.
    """

    @staticmethod
    def create_model(
        api_key: str,
        model_name: str = "deepseek/deepseek-v4-flash",
        base_url: str = "https://openrouter.ai/api/v1",
        app_title: str = "Agentic Substrate",
        app_referer: str = "https://agentic-substrate.local",
        rate_limiter: AsyncTokenBucketLimiter | None = None,
        timeout: float = 60.0,
    ) -> OpenAIResponsesModel:
        limiter = rate_limiter or AsyncTokenBucketLimiter()
        transport = RateLimitedAsyncTransport(rate_limiter=limiter)
        http_client = httpx.AsyncClient(transport=transport, timeout=timeout)

        custom_openai_client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            http_client=cast(Any, http_client),
            default_headers={
                "HTTP-Referer": app_referer,
                "X-Title": app_title,
            },
        )

        provider = OpenAIProvider(openai_client=custom_openai_client)
        return OpenAIResponsesModel(
            model_name=model_name,
            provider=provider,
        )
