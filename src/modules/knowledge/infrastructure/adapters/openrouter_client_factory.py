from typing import Any


class OpenRouterClientFactory:
    """
    Factory para instanciação de cliente OpenAI compatível com OpenRouter.
    Configura headers padrão como HTTP-Referer e X-Title para ranking e governança.
    """

    @staticmethod
    def create(
        api_key: str | None,
        base_url: str = "https://openrouter.ai/api/v1",
        app_title: str = "Agentic Substrate",
        app_referer: str = "https://agentic-substrate.local",
    ) -> Any | None:
        """Cria cliente assíncrono AsyncOpenAI por padrão."""
        return OpenRouterClientFactory.create_async(
            api_key=api_key,
            base_url=base_url,
            app_title=app_title,
            app_referer=app_referer,
        )

    @staticmethod
    def create_async(
        api_key: str | None,
        base_url: str = "https://openrouter.ai/api/v1",
        app_title: str = "Agentic Substrate",
        app_referer: str = "https://agentic-substrate.local",
    ) -> Any | None:
        if not api_key or not api_key.strip():
            return None

        try:
            from openai import AsyncOpenAI

            return AsyncOpenAI(
                api_key=api_key.strip(),
                base_url=base_url,
                default_headers={
                    "HTTP-Referer": app_referer,
                    "X-Title": app_title,
                },
            )
        except ImportError:
            return None

    @staticmethod
    def create_sync(
        api_key: str | None,
        base_url: str = "https://openrouter.ai/api/v1",
        app_title: str = "Agentic Substrate",
        app_referer: str = "https://agentic-substrate.local",
    ) -> Any | None:
        if not api_key or not api_key.strip():
            return None

        try:
            from openai import OpenAI

            return OpenAI(
                api_key=api_key.strip(),
                base_url=base_url,
                default_headers={
                    "HTTP-Referer": app_referer,
                    "X-Title": app_title,
                },
            )
        except ImportError:
            return None
