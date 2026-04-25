# Multi-LLM Provider Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-provider configuration support so different Claude model tiers route to different OpenAI-compatible LLM providers with automatic fallback.

**Architecture:** Replace single-provider .env config with a `providers.json` config file. A new `ProviderManager` holds independent client instances per provider. `ModelRouter` resolves Claude model names to provider+model pairs and executes fallback chains on failure.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, openai SDK, pytest

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `providers.json.example` | Create | Example multi-provider config |
| `src/core/provider_config.py` | Create | Pydantic models for config + JSON loader |
| `src/core/provider_manager.py` | Create | Manages provider client instances |
| `src/core/model_router.py` | Create | Resolves model to route entries with fallback |
| `src/core/config.py` | Rewrite | Load providers.json, remove old single-provider fields |
| `src/core/model_manager.py` | Delete | Replaced by model_router.py |
| `src/core/client.py` | Keep | No changes needed (already parameterized) |
| `src/api/endpoints.py` | Modify | Use ProviderManager + ModelRouter |
| `src/main.py` | Modify | Startup with new config |
| `src/conversion/request_converter.py` | Modify | Accept model string instead of model_manager |
| `.env.example` | Modify | Remove old provider fields |
| `tests/test_provider_config.py` | Create | Unit tests for config loading |
| `tests/test_model_router.py` | Create | Unit tests for routing + fallback |

---

### Task 1: Create Pydantic config models and JSON loader

**Files:**
- Create: `src/core/provider_config.py`
- Create: `providers.json.example`
- Create: `tests/test_provider_config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_provider_config.py`:

```python
"""Tests for provider config loading and validation."""
import json
import os
import pytest
import tempfile
from pathlib import Path


def _write_config(tmp_path: Path, config: dict) -> Path:
    """Helper: write config dict to a JSON file, return path."""
    p = tmp_path / "providers.json"
    p.write_text(json.dumps(config), encoding="utf-8")
    return p


def _minimal_config() -> dict:
    """A valid minimal providers config."""
    return {
        "providers": [
            {
                "name": "openai",
                "api_key": "sk-test-key",
                "base_url": "https://api.openai.com/v1",
            }
        ],
        "routing": {
            "opus": [{"provider": "openai", "model": "gpt-4o"}],
            "sonnet": [{"provider": "openai", "model": "gpt-4o"}],
            "haiku": [{"provider": "openai", "model": "gpt-4o-mini"}],
        },
    }


# --- load_providers_config ---

def test_load_valid_config(tmp_path):
    from src.core.provider_config import load_providers_config
    config = _minimal_config()
    path = _write_config(tmp_path, config)
    result = load_providers_config(str(path))
    assert len(result.providers) == 1
    assert result.providers[0].name == "openai"
    assert result.providers[0].api_key == "sk-test-key"
    assert result.providers[0].base_url == "https://api.openai.com/v1"
    assert result.providers[0].timeout == 90  # default
    assert result.providers[0].api_version is None  # default


def test_load_config_with_env_var_substitution(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "sk-from-env")
    config = _minimal_config()
    config["providers"][0]["api_key"] = "${TEST_API_KEY}"
    path = _write_config(tmp_path, config)

    from src.core.provider_config import load_providers_config
    result = load_providers_config(str(path))
    assert result.providers[0].api_key == "sk-from-env"


def test_load_config_file_not_found():
    from src.core.provider_config import load_providers_config, ConfigError
    with pytest.raises(ConfigError, match="Configuration file not found"):
        load_providers_config("/nonexistent/path/providers.json")


def test_load_config_invalid_json(tmp_path):
    from src.core.provider_config import load_providers_config, ConfigError
    p = tmp_path / "providers.json"
    p.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid JSON"):
        load_providers_config(str(p))


def test_load_config_missing_routing(tmp_path):
    from src.core.provider_config import load_providers_config, ConfigError
    config = {"providers": [{"name": "openai", "api_key": "sk-x", "base_url": "https://api.openai.com/v1"}]}
    path = _write_config(tmp_path, config)
    with pytest.raises(ConfigError, match="routing"):
        load_providers_config(str(path))


def test_load_config_routing_references_unknown_provider(tmp_path):
    from src.core.provider_config import load_providers_config, ConfigError
    config = _minimal_config()
    config["routing"]["opus"] = [{"provider": "nonexistent", "model": "gpt-4o"}]
    path = _write_config(tmp_path, config)
    with pytest.raises(ConfigError, match="nonexistent"):
        load_providers_config(str(path))


def test_load_config_duplicate_provider_names(tmp_path):
    from src.core.provider_config import load_providers_config, ConfigError
    config = _minimal_config()
    config["providers"].append({
        "name": "openai",
        "api_key": "sk-other",
        "base_url": "https://api.other.com/v1",
    })
    path = _write_config(tmp_path, config)
    with pytest.raises(ConfigError, match="Duplicate provider name"):
        load_providers_config(str(path))


def test_load_config_azure_provider(tmp_path):
    from src.core.provider_config import load_providers_config
    config = _minimal_config()
    config["providers"][0]["api_version"] = "2024-03-01-preview"
    config["providers"][0]["timeout"] = 120
    path = _write_config(tmp_path, config)
    result = load_providers_config(str(path))
    assert result.providers[0].api_version == "2024-03-01-preview"
    assert result.providers[0].timeout == 120


def test_load_config_multiple_providers(tmp_path):
    from src.core.provider_config import load_providers_config
    config = _minimal_config()
    config["providers"].append({
        "name": "deepseek",
        "api_key": "sk-ds-key",
        "base_url": "https://api.deepseek.com/v1",
    })
    config["routing"]["sonnet"] = [{"provider": "deepseek", "model": "deepseek-chat"}]
    path = _write_config(tmp_path, config)
    result = load_providers_config(str(path))
    assert len(result.providers) == 2
    assert result.routing["sonnet"][0].provider == "deepseek"


# --- resolve_env_vars ---

def test_resolve_env_vars_no_substitution():
    from src.core.provider_config import _resolve_env_var
    assert _resolve_env_var("sk-plain-key") == "sk-plain-key"


def test_resolve_env_var_with_env(monkeypatch):
    monkeypatch.setenv("MY_KEY", "resolved-value")
    from src.core.provider_config import _resolve_env_var
    assert _resolve_env_var("${MY_KEY}") == "resolved-value"


def test_resolve_env_var_missing_raises(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    from src.core.provider_config import _resolve_env_var, ConfigError
    with pytest.raises(ConfigError, match="MISSING_VAR"):
        _resolve_env_var("${MISSING_VAR}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd D:/code/claude-code-proxy && python -m pytest tests/test_provider_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.core.provider_config'`

- [ ] **Step 3: Write implementation**

Create `src/core/provider_config.py`:

```python
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
    """Load and validate providers.json configuration file.

    Args:
        config_path: Path to the providers.json file.

    Returns:
        Validated ProvidersConfig instance.

    Raises:
        ConfigError: If file not found, invalid JSON, or validation fails.
    """
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
```

Create `providers.json.example`:

```json
{
  "providers": [
    {
      "name": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1",
      "api_version": null,
      "timeout": 90
    },
    {
      "name": "deepseek",
      "api_key": "${DEEPSEEK_API_KEY}",
      "base_url": "https://api.deepseek.com/v1",
      "api_version": null,
      "timeout": 90
    }
  ],
  "routing": {
    "opus": [
      {"provider": "openai", "model": "gpt-4o"},
      {"provider": "deepseek", "model": "deepseek-chat"}
    ],
    "sonnet": [
      {"provider": "deepseek", "model": "deepseek-chat"},
      {"provider": "openai", "model": "gpt-4o-mini"}
    ],
    "haiku": [
      {"provider": "openai", "model": "gpt-4o-mini"}
    ]
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd D:/code/claude-code-proxy && python -m pytest tests/test_provider_config.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/provider_config.py providers.json.example tests/test_provider_config.py
git commit -m "feat: add provider config models and JSON loader with env var substitution"
```

---

### Task 2: Create ModelRouter with fallback

**Files:**
- Create: `src/core/model_router.py`
- Create: `tests/test_model_router.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_model_router.py`:

```python
"""Tests for ModelRouter with fallback support."""
import pytest
from unittest.mock import AsyncMock, MagicMock
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


# --- resolve tests ---

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


# --- _classify_tier tests ---

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


# --- is_retryable_error tests ---

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd D:/code/claude-code-proxy && python -m pytest tests/test_model_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.core.model_router'`

- [ ] **Step 3: Write implementation**

Create `src/core/model_router.py`:

```python
"""Model router: resolves Claude model names to provider+model route entries."""
from fastapi import HTTPException

from src.core.provider_config import ProvidersConfig, RouteEntry


# Direct-passthrough model prefixes (not Claude models)
_DIRECT_PASSTHROUGH_PREFIXES = ("gpt-", "o1-", "o3-", "o4-")
_PROVIDER_MODEL_PREFIXES = ("ep-", "doubao-", "deepseek-")


class ModelRouter:
    """Resolves Claude model names to ordered route entries with fallback support."""

    def __init__(self, config: ProvidersConfig):
        self._config = config
        self._providers_by_name = {p.name: p for p in config.providers}
        self._default_provider = config.providers[0] if config.providers else None

    def resolve(self, claude_model: str) -> list[RouteEntry]:
        """Resolve a Claude model name to an ordered list of route entries.

        Direct passthrough models (gpt-*, o1-*, ep-*, doubao-*, deepseek-*)
        are routed through the first configured provider with the model name
        unchanged.

        Claude models are classified into tiers (opus/sonnet/haiku) and routed
        according to the routing table. Unknown models default to opus routing.
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
        # Unknown models default to opus (most capable tier)
        return "opus"

    def is_retryable_error(self, error: HTTPException) -> bool:
        """Determine if an error should trigger fallback to the next provider.

        Retryable: 5xx server errors, 429 rate limiting, connection issues.
        Not retryable: 4xx client errors (except 429) - request is malformed.
        """
        status = error.status_code
        if status == 429:
            return True
        if status >= 500:
            return True
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd D:/code/claude-code-proxy && python -m pytest tests/test_model_router.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/model_router.py tests/test_model_router.py
git commit -m "feat: add ModelRouter with tier-based routing and passthrough support"
```

---

### Task 3: Create ProviderManager

**Files:**
- Create: `src/core/provider_manager.py`

- [ ] **Step 1: Write implementation**

Create `src/core/provider_manager.py`:

```python
"""Provider manager: creates and manages OpenAI client instances per provider."""
import logging
from typing import Dict, Optional

from src.core.provider_config import ProvidersConfig, ProviderEntry
from src.core.client import OpenAIClient

logger = logging.getLogger(__name__)


class ProviderManager:
    """Manages independent OpenAI client instances for each configured provider."""

    def __init__(self, config: ProvidersConfig, custom_headers: Optional[Dict[str, str]] = None):
        self._config = config
        self._custom_headers = custom_headers or {}
        self._clients: Dict[str, OpenAIClient] = {}
        self._init_clients()

    def _init_clients(self):
        """Create an OpenAIClient for each provider in the config."""
        for provider in self._config.providers:
            self._clients[provider.name] = OpenAIClient(
                api_key=provider.api_key,
                base_url=provider.base_url,
                timeout=provider.timeout,
                api_version=provider.api_version,
                custom_headers=self._custom_headers,
            )
            logger.info(f"Initialized client for provider '{provider.name}' -> {provider.base_url}")

    def get_client(self, provider_name: str) -> OpenAIClient:
        """Get the OpenAIClient for a named provider.

        Raises:
            KeyError: If provider_name is not configured.
        """
        client = self._clients.get(provider_name)
        if client is None:
            raise KeyError(f"Provider '{provider_name}' not found in configuration")
        return client

    @property
    def provider_names(self) -> list[str]:
        """List all configured provider names."""
        return list(self._clients.keys())

    def get_provider(self, provider_name: str) -> ProviderEntry:
        """Get the ProviderEntry config for a named provider."""
        for p in self._config.providers:
            if p.name == provider_name:
                return p
        raise KeyError(f"Provider '{provider_name}' not found")
```

- [ ] **Step 2: Verify import works**

Run: `cd D:/code/claude-code-proxy && python -c "from src.core.provider_manager import ProviderManager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/core/provider_manager.py
git commit -m "feat: add ProviderManager for multi-client instance management"
```

---

### Task 4: Rewrite config.py to load providers.json

**Files:**
- Modify: `src/core/config.py`

- [ ] **Step 1: Rewrite config.py**

Replace the entire content of `src/core/config.py` with:

```python
"""Application configuration: loads providers.json and server settings."""
import os
import sys
from typing import Optional

from src.core.provider_config import load_providers_config, ProvidersConfig, ConfigError


class Config:
    def __init__(self):
        # Provider configuration path
        self.providers_config_path = os.environ.get(
            "PROVIDERS_CONFIG", "providers.json"
        )

        # Load multi-provider configuration
        try:
            self.providers_config = load_providers_config(self.providers_config_path)
        except ConfigError as e:
            print(f"Configuration Error: {e}")
            sys.exit(1)

        # Anthropic API key for client validation (optional)
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            print("Warning: ANTHROPIC_API_KEY not set. Client API key validation will be disabled.")

        # Server settings
        self.host = os.environ.get("HOST", "0.0.0.0")
        self.port = int(os.environ.get("PORT", "8082"))
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.max_tokens_limit = int(os.environ.get("MAX_TOKENS_LIMIT", "4096"))
        self.min_tokens_limit = int(os.environ.get("MIN_TOKENS_LIMIT", "100"))
        self.request_timeout = int(os.environ.get("REQUEST_TIMEOUT", "90"))
        self.max_retries = int(os.environ.get("MAX_RETRIES", "2"))

    def validate_client_api_key(self, client_api_key):
        """Validate client's Anthropic API key."""
        if not self.anthropic_api_key:
            return True
        return client_api_key == self.anthropic_api_key

    def get_custom_headers(self):
        """Get custom headers from environment variables."""
        custom_headers = {}
        env_vars = dict(os.environ)
        for env_key, env_value in env_vars.items():
            if env_key.startswith("CUSTOM_HEADER_"):
                header_name = env_key[14:]
                if header_name:
                    header_name = header_name.replace("_", "-")
                    custom_headers[header_name] = env_value
        return custom_headers


try:
    config = Config()
    providers = config.providers_config
    print(f"Configuration loaded from: {config.providers_config_path}")
    print(f"Providers: {', '.join(p.name for p in providers.providers)}")
    for tier, routes in providers.routing.items():
        route_strs = [f"{r.provider}:{r.model}" for r in routes]
        print(f"  {tier} -> {', '.join(route_strs)}")
except SystemExit:
    raise
except Exception as e:
    print(f"Configuration Error: {e}")
    sys.exit(1)
```

- [ ] **Step 2: Verify config loads with a test providers.json**

Ensure `providers.json` exists in project root with valid content (e.g. copy from `providers.json.example` with test keys).

Run: `cd D:/code/claude-code-proxy && python -c "from src.core.config import config; print('Config loaded OK')"`
Expected: `Config loaded OK` with provider info printed

- [ ] **Step 3: Commit**

```bash
git add src/core/config.py
git commit -m "feat: rewrite config.py to load providers.json with multi-provider support"
```

---

### Task 5: Update endpoints and request_converter

**Files:**
- Modify: `src/api/endpoints.py`
- Modify: `src/conversion/request_converter.py`
- Delete: `src/core/model_manager.py`

- [ ] **Step 1: Update request_converter.py**

In `src/conversion/request_converter.py`, change the function signature at line 12-14:

From:
```python
def convert_claude_to_openai(
    claude_request: ClaudeMessagesRequest, model_manager
) -> Dict[str, Any]:
    """Convert Claude API request format to OpenAI format."""

    # Map model
    openai_model = model_manager.map_claude_model_to_openai(claude_request.model)
```

To:
```python
def convert_claude_to_openai(
    claude_request: ClaudeMessagesRequest, openai_model: str
) -> Dict[str, Any]:
    """Convert Claude API request format to OpenAI format."""
```

(The `openai_model` parameter is already resolved by `ModelRouter` - no mapping needed here.)

- [ ] **Step 2: Rewrite endpoints.py**

Replace the entire content of `src/api/endpoints.py` with:

```python
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import datetime
import uuid
from typing import Optional

from src.core.config import config
from src.core.logging import logger
from src.core.provider_manager import ProviderManager
from src.core.model_router import ModelRouter
from src.models.claude import ClaudeMessagesRequest, ClaudeTokenCountRequest
from src.conversion.request_converter import convert_claude_to_openai
from src.conversion.response_converter import (
    convert_openai_to_claude_response,
    convert_openai_streaming_to_claude_with_cancellation,
)

router = APIRouter()

# Initialize provider manager and model router
custom_headers = config.get_custom_headers()
provider_manager = ProviderManager(config.providers_config, custom_headers=custom_headers)
model_router = ModelRouter(config.providers_config)


async def validate_api_key(x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    """Validate the client's API key from either x-api-key header or Authorization header."""
    client_api_key = None
    if x_api_key:
        client_api_key = x_api_key
    elif authorization and authorization.startswith("Bearer "):
        client_api_key = authorization.replace("Bearer ", "")
    if not config.anthropic_api_key:
        return
    if not client_api_key or not config.validate_client_api_key(client_api_key):
        logger.warning("Invalid API key provided by client")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Please provide a valid Anthropic API key."
        )


@router.post("/v1/messages")
async def create_message(request: ClaudeMessagesRequest, http_request: Request, _: None = Depends(validate_api_key)):
    try:
        logger.debug(
            f"Processing Claude request: model={request.model}, stream={request.stream}"
        )

        request_id = str(uuid.uuid4())

        # Resolve routes for this model (with fallback chain)
        routes = model_router.resolve(request.model)

        last_error = None
        for route in routes:
            try:
                openai_client = provider_manager.get_client(route.provider)
                openai_request = convert_claude_to_openai(request, route.model)

                if await http_request.is_disconnected():
                    raise HTTPException(status_code=499, detail="Client disconnected")

                if request.stream:
                    openai_stream = openai_client.create_chat_completion_stream(
                        openai_request, request_id
                    )
                    return StreamingResponse(
                        convert_openai_streaming_to_claude_with_cancellation(
                            openai_stream,
                            request,
                            logger,
                            http_request,
                            openai_client,
                            request_id,
                        ),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Headers": "*",
                        },
                    )
                else:
                    openai_response = await openai_client.create_chat_completion(
                        openai_request, request_id
                    )
                    claude_response = convert_openai_to_claude_response(
                        openai_response, request
                    )
                    return claude_response

            except HTTPException as e:
                last_error = e
                if model_router.is_retryable_error(e) and len(routes) > 1:
                    logger.warning(
                        f"{route.provider}:{route.model} failed (HTTP {e.status_code}), "
                        f"falling back to next provider"
                    )
                    continue
                # Non-retryable error: raise immediately
                raise

        # All routes exhausted
        logger.error(f"All providers failed for model {request.model}")
        raise last_error or HTTPException(status_code=500, detail="All providers failed")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Unexpected error processing request: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/messages/count_tokens")
async def count_tokens(request: ClaudeTokenCountRequest, _: None = Depends(validate_api_key)):
    try:
        total_chars = 0
        if request.system:
            if isinstance(request.system, str):
                total_chars += len(request.system)
            elif isinstance(request.system, list):
                for block in request.system:
                    if hasattr(block, "text"):
                        total_chars += len(block.text)
        for msg in request.messages:
            if msg.content is None:
                continue
            elif isinstance(msg.content, str):
                total_chars += len(msg.content)
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if hasattr(block, "text") and block.text is not None:
                        total_chars += len(block.text)
        estimated_tokens = max(1, total_chars // 4)
        return {"input_tokens": estimated_tokens}
    except Exception as e:
        logger.error(f"Error counting tokens: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "providers": provider_manager.provider_names,
        "client_api_key_validation": bool(config.anthropic_api_key),
    }


@router.get("/test-connection")
async def test_connection():
    """Test API connectivity to the first configured provider."""
    first_provider = config.providers_config.providers[0]
    try:
        client = provider_manager.get_client(first_provider.name)
        first_route = config.providers_config.routing.get("haiku", [None])[0]
        test_model = first_route.model if first_route else "gpt-4o-mini"

        test_response = await client.create_chat_completion(
            {
                "model": test_model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5,
            }
        )
        return {
            "status": "success",
            "message": f"Successfully connected to provider '{first_provider.name}'",
            "model_used": test_model,
            "timestamp": datetime.now().isoformat(),
            "response_id": test_response.get("id", "unknown"),
        }
    except Exception as e:
        logger.error(f"API connectivity test failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "failed",
                "error_type": "API Error",
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
            },
        )


@router.get("/")
async def root():
    providers_info = []
    for p in config.providers_config.providers:
        providers_info.append({
            "name": p.name,
            "base_url": p.base_url,
        })
    routing_info = {}
    for tier, routes in config.providers_config.routing.items():
        routing_info[tier] = [f"{r.provider}:{r.model}" for r in routes]

    return {
        "message": "Claude-to-OpenAI API Proxy v2.0.0",
        "status": "running",
        "config": {
            "providers": providers_info,
            "routing": routing_info,
            "max_tokens_limit": config.max_tokens_limit,
            "client_api_key_validation": bool(config.anthropic_api_key),
        },
        "endpoints": {
            "messages": "/v1/messages",
            "count_tokens": "/v1/messages/count_tokens",
            "health": "/health",
            "test_connection": "/test-connection",
        },
    }
```

- [ ] **Step 3: Delete old model_manager.py**

Run: `rm src/core/model_manager.py`

- [ ] **Step 4: Verify imports work**

Run: `cd D:/code/claude-code-proxy && python -c "from src.api.endpoints import router; print('Endpoints OK')"`
Expected: `Endpoints OK`

- [ ] **Step 5: Commit**

```bash
git add src/api/endpoints.py src/conversion/request_converter.py
git rm src/core/model_manager.py
git commit -m "feat: update endpoints to use ProviderManager and ModelRouter with fallback"
```

---

### Task 6: Update main.py startup and .env.example

**Files:**
- Modify: `src/main.py`
- Modify: `.env.example`

- [ ] **Step 1: Update main.py**

Replace the content of `src/main.py` with:

```python
from fastapi import FastAPI
from src.api.endpoints import router as api_router
import uvicorn
import sys
from src.core.config import config

app = FastAPI(title="Claude-to-OpenAI API Proxy", version="2.0.0")

app.include_router(api_router)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Claude-to-OpenAI API Proxy v2.0.0")
        print("")
        print("Usage: python src/main.py")
        print("")
        print("Configuration:")
        print("  providers.json - Multi-provider configuration file (required)")
        print("  PROVIDERS_CONFIG - Path to providers.json (default: providers.json)")
        print("")
        print("Optional environment variables:")
        print("  ANTHROPIC_API_KEY - Expected Anthropic API key for client validation")
        print("  HOST - Server host (default: 0.0.0.0)")
        print("  PORT - Server port (default: 8082)")
        print("  LOG_LEVEL - Logging level (default: INFO)")
        print("  MAX_TOKENS_LIMIT - Token limit (default: 4096)")
        print("  MIN_TOKENS_LIMIT - Minimum token limit (default: 100)")
        print("  REQUEST_TIMEOUT - Request timeout in seconds (default: 90)")
        sys.exit(0)

    providers = config.providers_config

    print("Claude-to-OpenAI API Proxy v2.0.0")
    print(f"Config file: {config.providers_config_path}")
    print("Providers:")
    for p in providers.providers:
        print(f"  - {p.name}: {p.base_url}")
    print("Routing:")
    for tier, routes in providers.routing.items():
        route_strs = [f"{r.provider}:{r.model}" for r in routes]
        print(f"  {tier} -> {' -> '.join(route_strs)}")
    print(f"Max Tokens Limit: {config.max_tokens_limit}")
    print(f"Server: {config.host}:{config.port}")
    print(f"Client API Key Validation: {'Enabled' if config.anthropic_api_key else 'Disabled'}")
    print("")

    log_level = config.log_level.split()[0].lower()
    valid_levels = ["debug", "info", "warning", "error", "critical"]
    if log_level not in valid_levels:
        log_level = "info"

    uvicorn.run(
        "src.main:app",
        host=config.host,
        port=config.port,
        log_level=log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Update .env.example**

Replace `.env.example` with:

```env
# Required: Path to providers.json configuration file
# Default: providers.json (in project root)
PROVIDERS_CONFIG="providers.json"

# Optional: Expected Anthropic API key for client validation
# If set, clients must provide this exact API key to access the proxy
ANTHROPIC_API_KEY="your-expected-anthropic-api-key"

# Optional: Server settings
HOST="0.0.0.0"
PORT="8082"
LOG_LEVEL="INFO"
# DEBUG, INFO, WARNING, ERROR, CRITICAL

# Optional: Performance settings
MAX_TOKENS_LIMIT="4096"
MIN_TOKENS_LIMIT="100"
REQUEST_TIMEOUT="90"
MAX_RETRIES="2"

# Custom Headers Configuration
# Format: CUSTOM_HEADER_<HEADER_NAME>=value
# Underscores in header name are converted to hyphens
# CUSTOM_HEADER_ACCEPT="application/json"
# CUSTOM_HEADER_AUTHORIZATION="Bearer your-token"
# CUSTOM_HEADER_X_API_KEY="your-api-key"
```

- [ ] **Step 3: Verify server starts**

Run: `cd D:/code/claude-code-proxy && timeout 3 python start_proxy.py || true`
Expected: Server starts and prints provider config info, then exits after timeout

- [ ] **Step 4: Commit**

```bash
git add src/main.py .env.example
git commit -m "feat: update main.py startup and .env.example for multi-provider config"
```

---

### Task 7: Run full test suite and fix issues

**Files:**
- May modify: any file from Tasks 1-6 if tests reveal issues

- [ ] **Step 1: Run all tests**

Run: `cd D:/code/claude-code-proxy && python -m pytest tests/test_provider_config.py tests/test_model_router.py -v`
Expected: All tests PASS

- [ ] **Step 2: Verify server starts correctly**

Ensure `providers.json` exists in project root, then:

Run: `cd D:/code/claude-code-proxy && timeout 3 python start_proxy.py || true`
Expected: Server starts without errors, prints config info

- [ ] **Step 3: Fix any issues found**

Address any test failures or import errors.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "fix: resolve any issues found during full test suite run"
```

---

### Task 8: Update README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README with new providers.json configuration docs**

Update the README to document:
- New `providers.json` configuration format
- How to configure multiple providers
- Routing and fallback chain explanation
- Environment variable substitution syntax
- Migration from old .env configuration
- Remove references to BIG_MODEL/MIDDLE_MODEL/SMALL_MODEL

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for multi-provider configuration"
```
