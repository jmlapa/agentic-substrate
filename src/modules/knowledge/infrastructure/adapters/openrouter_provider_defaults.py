from typing import Any


class OpenRouterProviderDefaults:
    """
    Centralizador de configurações e políticas de provedor para chamadas à API OpenRouter.
    Garante que todas as requisições priorizem throughput máximo com suporte a fallbacks
    e supressão de overhead de reasoning não solicitado.
    """

    DEFAULT_SORT: str = "throughput"
    DEFAULT_ALLOW_FALLBACKS: bool = True
    DEFAULT_REASONING_EFFORT: str = "none"
    DEFAULT_REASONING_EXCLUDE: bool = True

    @classmethod
    def get_provider_routing(
        cls,
        sort: str = "throughput",
        allow_fallbacks: bool = True,
        order: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retorna o bloco de configuração de roteamento de provedor para a OpenRouter."""
        routing: dict[str, Any] = {
            "sort": sort,
            "allow_fallbacks": allow_fallbacks,
        }
        if order is not None:
            routing["order"] = order
        return routing

    @classmethod
    def get_reasoning_config(
        cls,
        effort: str = "none",
        exclude: bool = True,
    ) -> dict[str, Any]:
        """
        Retorna o bloco de controle de tokens de raciocínio para evitar
        latência desnecessária em tarefas estruturadas.
        """
        return {
            "effort": effort,
            "exclude": exclude,
        }

    @classmethod
    def get_throughput_extra_body(
        cls,
        allow_fallbacks: bool = True,
        order: list[str] | None = None,
        reasoning_effort: str = "none",
        exclude_reasoning: bool = True,
    ) -> dict[str, Any]:
        """
        Retorna o dicionário de extra_body pronto para clientes OpenAI / AsyncOpenAI
        configurando priorização de throughput e supressão de raciocínio.
        """
        return {
            "provider": cls.get_provider_routing(
                sort=cls.DEFAULT_SORT,
                allow_fallbacks=allow_fallbacks,
                order=order,
            ),
            "reasoning": cls.get_reasoning_config(
                effort=reasoning_effort,
                exclude=exclude_reasoning,
            ),
        }

    @classmethod
    def get_headers(
        cls,
        app_referer: str = "https://agentic-substrate.local",
        app_title: str = "Agentic Substrate",
        api_key: str | None = None,
    ) -> dict[str, str]:
        """Retorna os cabeçalhos padrão HTTP-Referer e X-Title para governança na OpenRouter."""
        headers: dict[str, str] = {
            "HTTP-Referer": app_referer,
            "X-Title": app_title,
        }
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        return headers
