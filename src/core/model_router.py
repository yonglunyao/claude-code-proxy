"""Model router: resolves Claude model names to provider+model route entries with round-robin load balancing."""
import itertools
from fastapi import HTTPException

from src.core.provider_config import ProvidersConfig, RouteEntry


# Direct-passthrough model prefixes (not Claude models)
_DIRECT_PASSTHROUGH_PREFIXES = ("gpt-", "o1-", "o3-", "o4-")
_PROVIDER_MODEL_PREFIXES = ("ep-", "doubao-", "deepseek-")


class ModelRouter:
    """Resolves Claude model names to route entries with round-robin and fallback support."""

    def __init__(self, config: ProvidersConfig):
        self._config = config
        self._providers_by_name = {p.name: p for p in config.providers}
        self._default_provider = config.providers[0] if config.providers else None
        # Round-robin counters per tier: tier -> cycling iterator over route indices
        self._rr_counters: dict[str, itertools.cycle] = {}
        self._rr_state: dict[str, int] = {}
        for tier in config.routing:
            n = len(config.routing[tier])
            self._rr_counters[tier] = itertools.cycle(range(n))
            self._rr_state[tier] = 0

    def resolve(self, claude_model: str) -> list[RouteEntry]:
        """Resolve a Claude model name to an ordered list of route entries.

        For Claude models, applies round-robin rotation on the tier's route list
        so consecutive requests are spread across providers.
        """
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
            return self._rotate_routes(tier, routes)

        # Fallback: if requested tier has no routes, try opus
        if tier != "opus":
            routes = self._config.routing.get("opus")
            if routes:
                return self._rotate_routes("opus", routes)

        # Last resort: first provider with original model name
        return [RouteEntry(provider=self._default_provider.name, model=claude_model)]

    def _rotate_routes(self, tier: str, routes: list[RouteEntry]) -> list[RouteEntry]:
        """Rotate routes list by the round-robin offset for this tier."""
        offset = next(self._rr_counters[tier])
        self._rr_state[tier] = offset
        return routes[offset:] + routes[:offset]

    def _classify_tier(self, model: str) -> str:
        """Classify a Claude model name into a tier: opus, sonnet, or haiku."""
        # 首先检查用户自定义的模型映射表
        if self._config.model_tier_mapping and model in self._config.model_tier_mapping:
            return self._config.model_tier_mapping[model]

        # 然后使用默认的关键字匹配
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
