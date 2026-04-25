"""Provider configuration models and loader."""
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel


class ConfigError(Exception):
    """Configuration loading or validation error."""
    pass


class ProviderEntry(BaseModel):
    """A single LLM provider configuration."""
    name: str
    api_key: str
    base_url: str
    api_version: Optional[str] = None
    timeout: int = 90


class RouteEntry(BaseModel):
    """A single route entry: provider name + model name."""
    provider: str
    model: str


class ProvidersConfig(BaseModel):
    """Top-level multi-provider configuration."""
    providers: List[ProviderEntry]
    routing: Dict[str, List[RouteEntry]]
    model_tier_mapping: Optional[Dict[str, str]] = None  # model_name -> tier


def _resolve_env_var(value: str) -> str:
    """Resolve ${ENV_VAR} references in a string value."""
    pattern = r"^\$\{(.+)\}$"
    match = re.match(pattern, value.strip())
    if not match:
        return value
    var_name = match.group(1)
    resolved = os.environ.get(var_name)
    if resolved is None:
        raise ConfigError(f"Environment variable '{var_name}' not set, referenced in config")
    return resolved


def load_providers_config(config_path: str) -> ProvidersConfig:
    """Load and validate providers.json configuration file."""
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {config_path}: {e}")

    # Resolve environment variables in api_key and base_url fields
    for provider in raw.get("providers", []):
        if "api_key" in provider:
            provider["api_key"] = _resolve_env_var(provider["api_key"])
        if "base_url" in provider:
            provider["base_url"] = _resolve_env_var(provider["base_url"])

    try:
        config = ProvidersConfig(**raw)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}")

    # Validate: no duplicate provider names
    names = [p.name for p in config.providers]
    if len(names) != len(set(names)):
        raise ConfigError("Duplicate provider names found in configuration")

    # Validate: all routing references point to existing providers
    provider_names = set(names)
    for tier, routes in config.routing.items():
        for route in routes:
            if route.provider not in provider_names:
                raise ConfigError(
                    f"Routing entry for '{tier}' references unknown provider '{route.provider}'"
                )

    return config
