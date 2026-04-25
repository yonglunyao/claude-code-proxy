# Claude Code Proxy

A proxy server that enables **Claude Code** to work with OpenAI-compatible API providers. Convert Claude API requests to OpenAI API calls, allowing you to use various LLM providers through the Claude Code CLI.

![Claude Code Proxy](demo.png)

## Features

- **Multi-Provider Support**: Configure multiple LLM providers (OpenAI, DeepSeek, Azure, local models) simultaneously
- **Smart Routing**: Route different Claude model tiers (opus/sonnet/haiku) to different providers
- **Automatic Fallback**: If a provider fails, automatically retry with the next provider in the chain
- **Full Claude API Compatibility**: Complete `/v1/messages` endpoint support
- **Function Calling**: Complete tool use support with proper conversion
- **Streaming Responses**: Real-time SSE streaming support
- **Image Support**: Base64 encoded image input
- **Custom Headers**: Automatic injection of custom HTTP headers for API requests
- **Error Handling**: Comprehensive error handling and logging

## Quick Start

### 1. Install Dependencies

```bash
# Using UV (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Configure

Create a `providers.json` file in the project root (copy from example):

```bash
cp providers.json.example providers.json
# Edit providers.json and add your API keys and routing
```

### 3. Start Server

```bash
# Direct run
python start_proxy.py

# Or with UV
uv run claude-code-proxy

# Or with docker compose
docker compose up -d
```

### 4. Use with Claude Code

```bash
# If ANTHROPIC_API_KEY is not set in the proxy:
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY="any-value" claude

# If ANTHROPIC_API_KEY is set in the proxy:
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY="exact-matching-key" claude
```

## Configuration

### providers.json

The proxy uses a `providers.json` file to configure multiple LLM providers and model routing.

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

#### Provider Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique provider identifier |
| `api_key` | Yes | API key. Supports `${ENV_VAR}` syntax for env var substitution |
| `base_url` | Yes | API endpoint URL |
| `api_version` | No | Azure API version (for Azure OpenAI only) |
| `timeout` | No | Request timeout in seconds (default: 90) |

#### Routing

The `routing` section maps Claude model tiers to providers:

| Tier | Matches |
|------|---------|
| `opus` | Claude models with "opus" in the name |
| `sonnet` | Claude models with "sonnet" in the name |
| `haiku` | Claude models with "haiku" in the name |

Each routing entry is an **ordered array** - the first entry is the primary provider, subsequent entries are fallback providers.

#### Fallback Chain

When a provider fails with a retryable error (timeout, 5xx, 429 rate limit), the proxy automatically tries the next provider in the chain:

```
Request: claude-sonnet-4-6
  -> deepseek:deepseek-chat -> Failed (timeout)
  -> openai:gpt-4o-mini -> Success -> Return response
```

#### Environment Variable Substitution

API keys and base URLs support `${ENV_VAR}` syntax to reference environment variables:

```json
{
  "api_key": "${OPENAI_API_KEY}",
  "base_url": "${OPENAI_BASE_URL}"
}
```

This keeps secrets out of the config file while using it for structure.

### Environment Variables

**Configuration:**

- `PROVIDERS_CONFIG` - Path to providers.json (default: `providers.json`)

**Security:**

- `ANTHROPIC_API_KEY` - Expected Anthropic API key for client validation
  - If set, clients must provide this exact API key to access the proxy
  - If not set, any API key will be accepted

**Server Settings:**

- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8082`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

**Performance:**

- `MAX_TOKENS_LIMIT` - Token limit (default: `4096`)
- `MIN_TOKENS_LIMIT` - Minimum token limit (default: `100`)
- `REQUEST_TIMEOUT` - Request timeout in seconds (default: `90`)

**Custom Headers:**

- `CUSTOM_HEADER_*` - Custom headers for API requests

### Custom Headers

Add custom headers by setting environment variables with the `CUSTOM_HEADER_` prefix:

```bash
CUSTOM_HEADER_ACCEPT="application/jsonstream"
CUSTOM_HEADER_AUTHORIZATION="Bearer your-token"
CUSTOM_HEADER_X_API_KEY="your-api-key"
```

### Direct Model Passthrough

You can also send requests with OpenAI model names directly - they pass through to the first configured provider:

```python
# These models bypass routing and go directly to the default provider
response = httpx.post("http://localhost:8082/v1/messages", json={
    "model": "gpt-4o",  # Direct passthrough
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Hello!"}]
})
```

Supported passthrough prefixes: `gpt-*`, `o1-*`, `o3-*`, `o4-*`, `ep-*`, `doubao-*`, `deepseek-*`

### Provider Examples

#### Single Provider (OpenAI)

```json
{
  "providers": [
    {
      "name": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1"
    }
  ],
  "routing": {
    "opus": [{"provider": "openai", "model": "gpt-4o"}],
    "sonnet": [{"provider": "openai", "model": "gpt-4o"}],
    "haiku": [{"provider": "openai", "model": "gpt-4o-mini"}]
  }
}
```

#### Azure OpenAI

```json
{
  "providers": [
    {
      "name": "azure",
      "api_key": "${AZURE_API_KEY}",
      "base_url": "https://your-resource.openai.azure.com",
      "api_version": "2024-03-01-preview"
    }
  ],
  "routing": {
    "opus": [{"provider": "azure", "model": "gpt-4"}],
    "sonnet": [{"provider": "azure", "model": "gpt-4"}],
    "haiku": [{"provider": "azure", "model": "gpt-35-turbo"}]
  }
}
```

#### Local Models (Ollama)

```json
{
  "providers": [
    {
      "name": "ollama",
      "api_key": "dummy-key",
      "base_url": "http://localhost:11434/v1"
    }
  ],
  "routing": {
    "opus": [{"provider": "ollama", "model": "llama3.1:70b"}],
    "sonnet": [{"provider": "ollama", "model": "llama3.1:70b"}],
    "haiku": [{"provider": "ollama", "model": "llama3.1:8b"}]
  }
}
```

## Usage Examples

### Basic Chat

```python
import httpx

response = httpx.post(
    "http://localhost:8082/v1/messages",
    json={
        "model": "claude-3-5-sonnet-20241022",  # Routes based on providers.json
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Hello!"}
        ]
    }
)
```

## Integration with Claude Code

```bash
# Start the proxy
python start_proxy.py

# Use Claude Code with the proxy
ANTHROPIC_BASE_URL=http://localhost:8082 claude

# Or set permanently
export ANTHROPIC_BASE_URL=http://localhost:8082
claude
```

## Testing

```bash
# Run unit tests
python -m pytest tests/ -v

# Run integration tests (requires running server)
python tests/test_main.py
```

## Development

### Using UV

```bash
# Install dependencies
uv sync

# Run server
uv run claude-code-proxy

# Format code
uv run black src/
uv run isort src/

# Type checking
uv run mypy src/
```

### Project Structure

```
claude-code-proxy/
├── src/
│   ├── main.py                     # FastAPI server
│   ├── api/endpoints.py            # API routes with fallback
│   ├── core/
│   │   ├── config.py               # App config (loads providers.json)
│   │   ├── provider_config.py      # Provider config models
│   │   ├── provider_manager.py     # Multi-provider client manager
│   │   ├── model_router.py         # Model routing with fallback
│   │   ├── client.py               # OpenAI async client
│   │   ├── constants.py            # API constants
│   │   └── logging.py              # Logging setup
│   ├── models/claude.py            # Claude request/response models
│   └── conversion/                 # Claude <-> OpenAI converters
├── tests/                          # Unit tests
├── providers.json.example          # Config template
├── .env.example                    # Environment variables template
├── start_proxy.py                  # Startup script
└── README.md
```

## Performance

- **Async/await** for high concurrency
- **Independent client pools** per provider
- **Streaming support** for real-time responses
- **Automatic fallback** for high availability
- **Configurable timeouts** and retries

## License

MIT License
