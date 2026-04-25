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
