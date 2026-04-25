"""Tests for provider config loading and validation."""
import json
import os
import pytest
from pathlib import Path


def _write_config(tmp_path: Path, config: dict) -> Path:
    p = tmp_path / "providers.json"
    p.write_text(json.dumps(config), encoding="utf-8")
    return p


def _minimal_config() -> dict:
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


def test_load_valid_config(tmp_path):
    from src.core.provider_config import load_providers_config
    config = _minimal_config()
    path = _write_config(tmp_path, config)
    result = load_providers_config(str(path))
    assert len(result.providers) == 1
    assert result.providers[0].name == "openai"
    assert result.providers[0].api_key == "sk-test-key"
    assert result.providers[0].base_url == "https://api.openai.com/v1"
    assert result.providers[0].timeout == 90
    assert result.providers[0].api_version is None


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
