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
