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

        # Resolve routes for this model (with round-robin + fallback chain)
        routes = model_router.resolve(request.model)

        last_error = None
        for i, route in enumerate(routes):
            try:
                if i == 0:
                    logger.info(f"[{request_id}] Route: {request.model} -> {route.provider}:{route.model}")

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
