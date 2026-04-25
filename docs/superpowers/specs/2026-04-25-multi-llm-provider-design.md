# Multi-LLM Provider Configuration Design

**Date**: 2026-04-25
**Status**: Draft
**Author**: Yonglun Yao

## Summary

Add support for configuring multiple OpenAI-compatible LLM providers in claude-code-proxy, enabling per-model routing to different API endpoints with automatic fallback chains.

## Motivation

Currently, claude-code-proxy supports only a single provider (one API key + base URL) configured via environment variables. Users who want to route different Claude model tiers to different providers (e.g., opus -> OpenAI GPT-4o, sonnet -> DeepSeek-V3, haiku -> Doubao-lite) cannot do so without manually changing configuration and restarting.

## Requirements

1. **Per-model routing**: Map different Claude model tiers (opus/sonnet/haiku) to different providers
2. **Multiple providers**: Configure multiple OpenAI-compatible API endpoints, each with independent credentials
3. **Fallback chains**: When primary provider fails, automatically try the next provider in the chain
4. **Configuration file**: Use an independent `providers.json` file for multi-provider configuration
5. **Complete replacement**: Replace the existing .env-based single provider configuration entirely

## Configuration Format

File: `providers.json` in project root.

```json
{
  "providers": [
    {
      "name": "openai",
      "api_key": "sk-xxx",
      "base_url": "https://api.openai.com/v1",
      "api_version": null,
      "timeout": 90
    },
    {
      "name": "deepseek",
      "api_key": "sk-yyy",
      "base_url": "https://api.deepseek.com/v1",
      "api_version": null,
      "timeout": 90
    },
    {
      "name": "azure",
      "api_key": "sk-zzz",
      "base_url": "https://xxx.openai.azure.com",
      "api_version": "2024-03-01-preview",
      "timeout": 120
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

### Field descriptions

**Provider fields:**
- `name` (required): Unique provider identifier, used in routing references
- `api_key` (required): API key for authentication. Supports env var substitution: `"${OPENAI_API_KEY}"`
- `base_url` (required): API endpoint URL
- `api_version` (optional): Azure API version, null for non-Azure providers
- `timeout` (optional, default 90): Request timeout in seconds

**Routing fields:**
- `routing` keys: Claude model tier names - `opus`, `sonnet`, `haiku`
- Each routing entry is an ordered array of `{provider, model}` objects
- Array order defines the fallback chain: first entry is primary, subsequent are fallbacks

### Environment variable substitution

API keys and base URLs support `${ENV_VAR}` syntax to reference environment variables:

```json
{
  "api_key": "${OPENAI_API_KEY}",
  "base_url": "${OPENAI_BASE_URL}"
}
```

This allows keeping secrets in environment variables while using the config file for structure.

## Architecture

### File changes

| File | Change Type | Description |
|------|-------------|-------------|
| `providers.json` | New | Multi-provider configuration file |
| `providers.json.example` | New | Example configuration file |
| `src/core/config.py` | Rewrite | Load providers.json, parse routing table, validate config |
| `src/core/model_manager.py` | Rewrite | Route-based model mapping with fallback |
| `src/core/client.py` | Refactor | Create independent client instances per provider |
| `src/api/endpoints.py` | Modify | Use new model_manager and client interfaces |
| `.env.example` | Modify | Remove old single-provider vars, add PROVIDERS_CONFIG path |
| `src/main.py` | Modify | Load provider config at startup |

### New classes

```
ProviderConfig     - Single provider config (name, api_key, base_url, timeout, api_version)
RouteEntry         - Single route entry (provider_name, model_name)
ProviderManager    - Manages all provider instances, provides client lookup by provider name
ModelRouter        - Resolves Claude model to RouteEntry list, executes fallback chain
```

### Request flow

```
Request arrives at /v1/messages
  -> API key validation (existing logic)
  -> ModelRouter.resolve(claude_model) -> List[RouteEntry]
  -> For each RouteEntry:
      -> ProviderManager.get_client(provider_name) -> AsyncOpenAI client
      -> Convert Claude request -> OpenAI request (existing logic)
      -> Send to provider via client
      -> If success: convert response -> return
      -> If retryable error: log + try next RouteEntry
  -> All failed: return last error
```

## Fallback Mechanism

### Retryable errors (trigger fallback)

- Connection timeout
- HTTP 5xx server errors
- HTTP 429 rate limiting
- Connection refused

### Non-retryable errors (fail immediately)

- HTTP 4xx client errors (except 429) - request itself is malformed
- HTTP 401 authentication failure - provider config is wrong
- Invalid response format - provider incompatibility

### Error reporting

When all providers fail, return the error from the last attempted provider. Log each fallback attempt:

```
WARN: deepseek:deepseek-chat failed (ConnectionTimeout), falling back to openai:gpt-4o-mini
ERROR: All providers failed for model claude-sonnet-4-6
```

## Out of Scope

- Load balancing strategies (round-robin, weighted) - can be added later
- Request-level provider selection - routing is config-based only
- Provider health checking - fallback is reactive, not proactive
- Multiple configuration file formats - JSON only for now
- Streaming partial fallback - if streaming starts and fails mid-stream, no fallback

## Success Criteria

1. Users can define multiple providers with independent credentials in `providers.json`
2. Claude model tiers (opus/sonnet/haiku) route to configured providers correctly
3. When primary provider fails, fallback to next provider in chain works
4. Existing request conversion logic (Claude <-> OpenAI format) continues to work
5. Direct model passthrough (gpt-*, o1-*, ep-*, doubao-*, deepseek-*) still works
6. Configuration errors are caught at startup with clear error messages
