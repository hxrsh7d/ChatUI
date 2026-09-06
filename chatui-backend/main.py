"""
ChatUI AI Gateway backend.

This is the FastAPI application entrypoint. The actual provider logic,
document/RAG pipeline, web search, and image generation live in their own
modules (providers/, documents/, search/, images/, api/) -- this file only
wires them together and owns the two endpoints that need long-lived local
process state: llama-server lifecycle (autostart/shutdown) and the unified
streaming chat endpoint.

Existing API contracts are preserved:
  GET  /health
  GET  /v1/models
  POST /api/models/load
  POST /api/chat            (SSE)
New endpoints added:
  POST /api/documents        (multipart upload)
  DELETE /api/documents/{id}
  GET  /api/providers
  POST /api/providers/test
"""

import hmac
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

import config
from logging_config import get_logger, setup_logging
from metrics import metrics

setup_logging()
logger = get_logger("main")

from api.chat import stream_chat_response
from api.documents import router as documents_router
from api.metrics import router as metrics_router
from api.providers import router as providers_router
from providers.registry import registry
from rate_limit import RateLimiter

chat_limiter = RateLimiter(config.RATE_LIMIT_CHAT_PER_MINUTE, window_seconds=60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting up")
    await registry.local.autostart()
    try:
        yield
    finally:
        logger.info("shutting down")
        await registry.local.shutdown()


app = FastAPI(title="ChatUI AI Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Access control + request observability
#
# Combined into one middleware (rather than two separate ones) so their
# relative order is never ambiguous: every request is timed and logged/
# recorded in metrics regardless of whether it was authorized, which is
# useful for spotting repeated unauthorized access attempts.
#
# If config.ACCESS_TOKEN is unset, every request passes through unchanged --
# this preserves frictionless solo/personal use with zero setup. Once set
# (e.g. before sharing this instance with anyone else), every request must
# present a matching "Authorization: Bearer <token>" header, checked with a
# constant-time comparison to avoid leaking the token via timing. The root
# "/" liveness ping stays open so basic uptime checks don't need a token.
# ============================================================================

@app.middleware("http")
async def observability_and_access_control(request: Request, call_next):
    start = time.perf_counter()
    client_host = request.client.host if request.client else "unknown"

    if config.ACCESS_TOKEN and request.method != "OPTIONS" and request.url.path != "/":
        expected = f"Bearer {config.ACCESS_TOKEN}"
        provided = request.headers.get("authorization", "")
        if not hmac.compare_digest(provided, expected):
            duration = time.perf_counter() - start
            metrics.record_request(request.method, request.url.path, 401, duration)
            logger.warning(
                "unauthorized request",
                extra={"extra_fields": {"method": request.method, "path": request.url.path, "client": client_host}},
            )
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    response = await call_next(request)

    duration = time.perf_counter() - start
    metrics.record_request(request.method, request.url.path, response.status_code, duration)
    logger.info(
        "request",
        extra={
            "extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 1),
                "client": client_host,
            }
        },
    )
    return response


app.include_router(documents_router, prefix="/api")
app.include_router(providers_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")


# ============================================================================
# Root / health
# ============================================================================

@app.get("/")
async def root():
    return {"status": "ok", "service": "ChatUI AI Gateway"}


@app.get("/health")
async def health():
    local_health = await registry.local.health()

    provider_status = {}
    for provider in registry.all_providers():
        if provider is registry.local:
            continue
        try:
            provider_status[provider.id] = await provider.is_configured()
        except Exception:
            provider_status[provider.id] = False

    return {
        **local_health,
        "providers": provider_status,
    }


# ============================================================================
# Model discovery (merges local + every configured cloud provider)
# ============================================================================

@app.get("/v1/models")
async def list_models():
    models = await registry.list_all_models()
    return {"object": "list", "data": [m.to_dict() for m in models]}


# ============================================================================
# Load / switch local model (unchanged contract)
# ============================================================================

@app.post("/api/models/load")
async def load_model(request: dict):
    model_name = request.get("model")
    return await registry.local.load_model(model_name)


# ============================================================================
# Chat streaming (unified gateway across all providers)
# ============================================================================

@app.post("/api/chat")
async def chat(request: Request, body: dict):
    if config.RATE_LIMIT_ENABLED:
        client_ip = request.client.host if request.client else "unknown"
        allowed, retry_after = chat_limiter.check(client_ip)
        if not allowed:

            async def rate_limited_stream():
                message = f"Too many chat requests from this client. Try again in {retry_after:.0f}s."
                yield "data: " + json.dumps({"type": "error", "message": message}) + "\n\n"

            return StreamingResponse(
                rate_limited_stream(),
                media_type="text/event-stream",
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

    async def stream():
        try:
            async for event in stream_chat_response(body):
                yield "data: " + json.dumps(event) + "\n\n"
        except Exception as exc:  # noqa: BLE001
            # Last-resort safety net so a bug in routing/RAG/search never
            # hangs the connection without telling the frontend anything.
            yield "data: " + json.dumps({"type": "error", "message": f"Unexpected server error: {exc}"}) + "\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
