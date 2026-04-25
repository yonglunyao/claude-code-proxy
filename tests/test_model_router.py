"""Tests for ModelRouter with fallback support."""
import pytest
from fastapi import HTTPException

from src.core.provider_config import ProviderEntry, RouteEntry


def _make_config():
    from src.core.provider_config import ProvidersConfig
    return ProvidersConfig(
        providers=[
            ProviderEntry(name="openai", api_key="sk-test", base_url="https://api.openai.com/v1"),
            ProviderEntry(name="deepseek", api_key="sk-ds", base_url="https://api.deepseek.com/v1"),
        ],
        routing={
            "opus": [
                RouteEntry(provider="openai", model="gpt-4o"),
                RouteEntry(provider="deepseek", model="deepseek-chat"),
            ],
            "sonnet": [
                RouteEntry(provider="deepseek", model="deepseek-chat"),
            ],
            "haiku": [
                RouteEntry(provider="openai", model="gpt-4o-mini"),
            ],
        },
    )


def test_resolve_opus_returns_ordered_routes():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    routes = router.resolve("claude-opus-4-6")
    assert len(routes) == 2
    assert routes[0].provider == "openai"
    assert routes[0].model == "gpt-4o"
    assert routes[1].provider == "deepseek"
    assert routes[1].model == "deepseek-chat"


def test_resolve_sonnet_returns_single_route():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    routes = router.resolve("claude-sonnet-4-6")
    assert len(routes) == 1
    assert routes[0].provider == "deepseek"
    assert routes[0].model == "deepseek-chat"


def test_resolve_haiku_returns_single_route():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    routes = router.resolve("claude-haiku-4-5")
    assert len(routes) == 1
    assert routes[0].provider == "openai"
    assert routes[0].model == "gpt-4o-mini"


def test_resolve_direct_openai_model_passes_through():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    routes = router.resolve("gpt-4o")
    assert len(routes) >= 1
    assert routes[0].model == "gpt-4o"


def test_resolve_direct_deepseek_model_passes_through():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    routes = router.resolve("deepseek-chat")
    assert len(routes) >= 1
    assert routes[0].model == "deepseek-chat"


def test_resolve_ep_model_passes_through():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    routes = router.resolve("ep-20240101-model")
    assert len(routes) >= 1
    assert routes[0].model == "ep-20240101-model"


def test_resolve_doubao_model_passes_through():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    routes = router.resolve("doubao-pro-32k")
    assert len(routes) >= 1
    assert routes[0].model == "doubao-pro-32k"


def test_resolve_unknown_model_defaults_to_opus():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    routes = router.resolve("claude-unknown-model")
    assert len(routes) == 2
    assert routes[0].provider == "openai"


def test_classify_tier_haiku():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    assert router._classify_tier("claude-3-5-haiku-20241022") == "haiku"
    assert router._classify_tier("claude-haiku-4-5") == "haiku"


def test_classify_tier_sonnet():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    assert router._classify_tier("claude-3-5-sonnet-20241022") == "sonnet"
    assert router._classify_tier("claude-sonnet-4-6") == "sonnet"


def test_classify_tier_opus():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    assert router._classify_tier("claude-opus-4-6") == "opus"
    assert router._classify_tier("claude-3-opus-20240229") == "opus"


def test_classify_tier_unknown_defaults_opus():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    assert router._classify_tier("claude-some-new-model") == "opus"


def test_is_retryable_500():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    assert router.is_retryable_error(HTTPException(status_code=500, detail="err")) is True


def test_is_retryable_429():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    assert router.is_retryable_error(HTTPException(status_code=429, detail="rate limited")) is True


def test_is_retryable_401_is_not_retryable():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    assert router.is_retryable_error(HTTPException(status_code=401, detail="unauthorized")) is False


def test_is_retryable_400_is_not_retryable():
    from src.core.model_router import ModelRouter
    router = ModelRouter(_make_config())
    assert router.is_retryable_error(HTTPException(status_code=400, detail="bad request")) is False
