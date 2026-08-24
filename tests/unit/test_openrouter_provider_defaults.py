from src.modules.knowledge.infrastructure.adapters.openrouter_client_factory import (
    OpenRouterClientFactory,
)
from src.modules.knowledge.infrastructure.adapters.openrouter_provider_defaults import (
    OpenRouterProviderDefaults,
)


def test_openrouter_provider_defaults_routing_structure() -> None:
    routing = OpenRouterProviderDefaults.get_provider_routing()
    assert routing == {
        "sort": "throughput",
        "allow_fallbacks": True,
    }

    custom_routing = OpenRouterProviderDefaults.get_provider_routing(
        sort="latency",
        allow_fallbacks=False,
        order=["DeepInfra", "Together"],
    )
    assert custom_routing == {
        "sort": "latency",
        "allow_fallbacks": False,
        "order": ["DeepInfra", "Together"],
    }


def test_openrouter_provider_defaults_reasoning_config() -> None:
    reasoning = OpenRouterProviderDefaults.get_reasoning_config()
    assert reasoning == {
        "effort": "none",
        "exclude": True,
    }


def test_openrouter_provider_defaults_throughput_extra_body() -> None:
    extra_body = OpenRouterProviderDefaults.get_throughput_extra_body()
    assert "provider" in extra_body
    assert extra_body["provider"]["sort"] == "throughput"
    assert extra_body["provider"]["allow_fallbacks"] is True
    assert "reasoning" in extra_body
    assert extra_body["reasoning"]["effort"] == "none"
    assert extra_body["reasoning"]["exclude"] is True


def test_openrouter_provider_defaults_headers() -> None:
    headers = OpenRouterProviderDefaults.get_headers(
        app_referer="https://custom.app",
        app_title="Custom App Title",
        api_key="sk-or-secret",
    )
    assert headers["HTTP-Referer"] == "https://custom.app"
    assert headers["X-Title"] == "Custom App Title"
    assert headers["Authorization"] == "Bearer sk-or-secret"


def test_openrouter_client_factory_throughput_shortcut() -> None:
    shortcut_extra_body = OpenRouterClientFactory.get_throughput_extra_body()
    assert shortcut_extra_body == OpenRouterProviderDefaults.get_throughput_extra_body()
