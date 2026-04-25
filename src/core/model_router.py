"""Model router: resolves Claude model names to provider+model route entries."""
from fastapi import HTTPException

from src.core.provider_config import ProvidersConfig, RouteEntry


# Direct-passthrough model prefixes (not Claude models)
_DIRECT_PASSTHROUGH_PREFIXES = ("gpt-", "o1-", "o3-", "o4-")
_PROVIDER_MODEL_PREFIXES = ("ep-", "doubao-", "deepseek-")


class ModelRouter:
    """Resolves Claude model names to an ordered list of route entries with fallback support."""

    def __init__(self, config: ProvidersConfig):
        self._config = config
        self._providers_by_name = {p.name: p for p in config.providers}
        self._default_provider = config.providers[0] if config.providers else None

    def resolve(self, claude_model: str) -> list[RouteEntry]:
        """Resolve a Claude model name to an ordered list of route entries."""
        # Direct OpenAI model passthrough
        if claude_model.startswith(_DIRECT_PASSTHROUGH_PREFIXES):
            return [RouteEntry(provider=self._default_provider.name, model=claude_model)]

        # Other provider model passthrough
        if claude_model.startswith(_PROVIDER_MODEL_PREFIXES):
            return [RouteEntry(provider=self._default_provider.name, model=claude_model)]

        # Classify Claude model into tier
        tier = self._classify_tier(claude_model)
        routes = self._config.routing.get(tier)
        if routes:
            return list(routes)

        # Fallback: if requested tier has no routes, try opus
        if tier != "opus":
            routes = self._config.routing.get("opus")
            if routes:
                return list(routes)

        # Last resort: first provider with original model name
        return [RouteEntry(provider=self._default_provider.name, model=claude_model)]

    def _classify_tier(self, model: str) -> str:
        """Classify a Claude model name into a tier: opus, sonnet, or haiku."""
        model_lower = model.lower()
        if "haiku" in model_lower:
            return "haiku"
        if "sonnet" in model_lower:
            return "sonnet"
        if "opus" in model_lower:
            return "opus"
        return "opus"

    def is_retryable_error(self, error: HTTPException) -> bool:
        """Determine if an error should trigger fallback."""
        status = error.status_code
        if status == 429:
            return True
        if status >= 500:
            return True
        return False
