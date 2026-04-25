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
