"""Bantu-OS Network API Server — Phase 3

HTTP API with API key auth, rate limiting, and full kernel/session integration.
Serves external clients (web, mobile) over HTTP while the kernel remains Unix-socket-only.

Endpoints:
  GET  /health                          — health check
  POST /api/auth/verify                 — verify API key
  POST /api/auth/key                    — create API key
  POST /api/ai/chat                    — send a chat message
  GET  /api/sessions                    — list sessions
  POST /api/sessions                   — create session
  GET  /api/sessions/:id               — get session info
  DELETE /api/sessions/:id            — destroy session
  GET  /api/sessions/:id/history       — get conversation history
  DELETE /api/sessions/:id/history     — clear session history
  POST /api/sessions/:id/tools/:tool   — call a tool
  GET  /api/tools                       — list available tools
  GET  /api/tools/:name                 — get tool schema

Auth: Authorization: Bearer <api_key> header on all /api/* routes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from typing import Any, Dict, Optional

from aiohttp import web

from .api_key_store import APIKeyStore
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# ─── Kernel bridge ────────────────────────────────────────────────────────────

SOCKET_PATH = "/tmp/bantu.sock"
ADMIN_SOCK = "/tmp/bantu-admin.sock"


async def _socket_request(payload: dict, timeout: float = 30.0) -> dict:
    """Send JSON request to kernel socket, return parsed response."""

    async def do_request(sock_path: str) -> dict:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(sock_path), timeout=5.0
        )
        try:
            await writer.write((json.dumps(payload) + "\n").encode())
            await writer.drain()
            response = await asyncio.wait_for(reader.readline(), timeout=timeout)
            return json.loads(response.decode())
        finally:
            writer.close()
            await writer.wait_closed()

    try:
        return await do_request(SOCKET_PATH)
    except Exception:
        try:
            return await do_request(ADMIN_SOCK)
        except Exception as e:
            return {"ok": False, "error": f"Socket unavailable: {e}"}


# ─── Auth middleware ───────────────────────────────────────────────────────────

_api_key_store: Optional[APIKeyStore] = None


@web.middleware
async def auth_middleware(request: web.Request, handler) -> web.Response:
    """Require valid API key on all /api/* routes."""

    if not request.path.startswith("/api/"):
        return await handler(request)

    if request.path in ("/api/auth/verify", "/api/auth/key"):
        return await handler(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return _json_error(401, "Missing or invalid Authorization header")

    key = auth_header[7:]
    if _api_key_store is None or not await _api_key_store.verify(key):
        return _json_error(401, "Invalid API key")

    rate_limiter: RateLimiter = request.app["rate_limiter"]
    if not await rate_limiter.check(key):
        return _json_error(429, "Rate limit exceeded")

    request["api_key"] = key
    request["key_info"] = await _api_key_store.get_key_info(key)

    return await handler(request)


# ─── Response helpers ──────────────────────────────────────────────────────────


def _json(data: Any, status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps(data, ensure_ascii=False),
        status=status,
        content_type="application/json",
    )


def _json_error(status: int, message: str) -> web.Response:
    return web.Response(
        text=json.dumps({"error": message}, ensure_ascii=False),
        status=status,
        content_type="application/json",
    )


# ─── Routes ───────────────────────────────────────────────────────────────────


async def health(request: web.Request) -> web.Response:
    """GET /health — lightweight health check."""
    return _json({"status": "ok", "service": "bantu-os-api", "version": "0.1.0"})


async def auth_verify(request: web.Request) -> web.Response:
    """POST /api/auth/verify — verify an API key."""
    global _api_key_store
    body = await request.json()
    key = body.get("api_key", "")
    if not key:
        return _json_error(400, "api_key required")
    if _api_key_store is None or not await _api_key_store.verify(key):
        return _json_error(401, "Invalid API key")
    info = await _api_key_store.get_key_info(key)
    return _json(
        {"ok": True, "key_id": info.get("key_id"), "tier": info.get("tier", "free")}
    )


async def auth_create_key(request: web.Request) -> web.Response:
    """POST /api/auth/key — create a new API key (admin only in production)."""
    global _api_key_store
    body = await request.json()
    tier = body.get("tier", "free")
    label = body.get("label", "")
    if _api_key_store is None:
        return _json_error(500, "API key store not initialized")
    key, info = await _api_key_store.create_key(tier=tier, label=label)
    return _json(
        {"api_key": key, "key_id": info["key_id"], "tier": info["tier"]}, status=201
    )


async def ai_chat(request: web.Request) -> web.Response:
    """POST /api/ai/chat — send a message to the AI."""
    body = await request.json()
    text = body.get("text", "")
    session_id = body.get("session_id")
    system_prompt = body.get("system_prompt")
    temperature = float(body.get("temperature", 0.7))

    if not text:
        return _json_error(400, "'text' field required")

    kernel_req: Dict[str, Any] = {"cmd": "ai", "text": text}
    if session_id:
        kernel_req["session_id"] = session_id
    if system_prompt:
        kernel_req["system_prompt"] = system_prompt
    if temperature != 0.7:
        kernel_req["temperature"] = temperature

    response = await _socket_request(kernel_req)

    if response.get("ok"):
        result = response.get("result", "")
        out: Dict[str, Any] = {"response": result}
        if session_id:
            out["session_id"] = session_id
        elif response.get("session_id"):
            out["session_id"] = response["session_id"]
        return _json(out)
    return _json_error(500, response.get("error", "AI request failed"))


async def session_list(request: web.Request) -> web.Response:
    """GET /api/sessions — list active sessions."""
    req = {"cmd": "admin_list_sessions"}
    result = await _socket_request(req, timeout=10.0)
    if result.get("ok"):
        return _json({"sessions": result.get("result", {}).get("sessions", [])})
    return _json_error(500, result.get("error", "Failed to list sessions"))


async def session_create(request: web.Request) -> web.Response:
    """POST /api/sessions — create a new session."""
    body = await request.json()
    username = body.get("username", f"user_{secrets.token_hex(4)}")
    req = {"cmd": "login", "username": username}
    result = await _socket_request(req, timeout=10.0)
    if result.get("ok"):
        return _json(
            {
                "ok": True,
                "session_id": result.get("result", {}).get("session_id"),
                "username": username,
            },
            status=201,
        )
    return _json_error(500, result.get("error", "Failed to create session"))


async def session_get(request: web.Request) -> web.Response:
    """GET /api/sessions/:id — get session info."""
    session_id = request.match_info["id"]
    req = {"cmd": "session_status", "session_id": session_id}
    result = await _socket_request(req, timeout=10.0)
    if result.get("ok"):
        return _json(result.get("result", {}))
    return _json_error(404, result.get("error", "Session not found"))


async def session_delete(request: web.Request) -> web.Response:
    """DELETE /api/sessions/:id — destroy session."""
    session_id = request.match_info["id"]
    req = {"cmd": "logout", "session_id": session_id}
    result = await _socket_request(req, timeout=10.0)
    if result.get("ok"):
        return _json({"ok": True})
    return _json_error(500, result.get("error", "Failed to destroy session"))


async def session_history(request: web.Request) -> web.Response:
    """GET/DELETE /api/sessions/:id/history."""
    session_id = request.match_info["id"]
    if request.method == "DELETE":
        req = {"cmd": "clear_history", "session_id": session_id}
    else:
        req = {"cmd": "session_history", "session_id": session_id}
    result = await _socket_request(req, timeout=10.0)
    if result.get("ok"):
        return _json(result.get("result", {}))
    return _json_error(500, result.get("error", "Failed to access history"))


async def session_tool(request: web.Request) -> web.Response:
    """POST /api/sessions/:id/tools/:tool — call a tool in a session context."""
    session_id = request.match_info["id"]
    tool_name = request.match_info["tool"]
    body = await request.json()
    args = body.get("args", {})
    req = {
        "cmd": "tool",
        "session_id": session_id,
        "tool": tool_name,
        "method": body.get("method", "execute"),
        "args": args,
    }
    result = await _socket_request(req, timeout=30.0)
    if result.get("ok"):
        return _json({"ok": True, "result": result.get("result")})
    return _json_error(500, result.get("error", f"Tool '{tool_name}' failed"))


async def tools_list(request: web.Request) -> web.Response:
    """GET /api/tools — list all available tools and their schemas."""
    req = {"cmd": "tools_list"}
    result = await _socket_request(req, timeout=10.0)
    if result.get("ok"):
        return _json({"tools": result.get("result", {}).get("tools", [])})
    return _json_error(500, result.get("error", "Failed to list tools"))


async def tool_schema(request: web.Request) -> web.Response:
    """GET /api/tools/:name — get schema for a specific tool."""
    tool_name = request.match_info["name"]
    req = {"cmd": "tool_schema", "tool": tool_name}
    result = await _socket_request(req, timeout=10.0)
    if result.get("ok"):
        return _json(result.get("result", {}))
    return _json_error(404, result.get("error", f"Tool '{tool_name}' not found"))


async def cors_preflight(request: web.Request) -> web.Response:
    """Handle CORS preflight requests."""
    origin = request.headers.get("Origin", "*")
    resp = web.Response()
    resp.headers["Access-Control-Allow-Origin"] = origin
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    resp.headers["Access-Control-Max-Age"] = "86400"
    return resp


# ─── App setup ───────────────────────────────────────────────────────────────


def create_app(
    api_key_store: Optional[APIKeyStore] = None,
    rate_limiter: Optional[RateLimiter] = None,
) -> web.Application:
    """Build and configure the aiohttp application."""
    global _api_key_store
    if api_key_store is not None:
        _api_key_store = api_key_store

    app = web.Application(middlewares=[auth_middleware])
    app["rate_limiter"] = rate_limiter or RateLimiter()
    app["api_key_store"] = api_key_store or APIKeyStore()

    if api_key_store is not None:
        _api_key_store = api_key_store

    # Routes
    app.router.add_get("/health", health)
    app.router.add_post("/api/auth/verify", auth_verify)
    app.router.add_post("/api/auth/key", auth_create_key)
    app.router.add_post("/api/ai/chat", ai_chat)

    app.router.add_get("/api/sessions", session_list)
    app.router.add_post("/api/sessions", session_create)
    app.router.add_get(r"/api/sessions/{id}", session_get)
    app.router.add_delete(r"/api/sessions/{id}", session_delete)
    app.router.add_get(r"/api/sessions/{id}/history", session_history)
    app.router.add_delete(r"/api/sessions/{id}/history", session_history)
    app.router.add_post(r"/api/sessions/{id}/tools/{tool}", session_tool)

    app.router.add_get("/api/tools", tools_list)
    app.router.add_get(r"/api/tools/{name}", tool_schema)

    # CORS
    app.router.add_options("/api/{tail:.+}", cors_preflight)
    app.router.add_options("/health", cors_preflight)

    return app


# ─── CLI entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run the API server."""
    import argparse

    parser = argparse.ArgumentParser(description="Bantu-OS Network API Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--api-keys-path", default="/etc/bantu/api_keys.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[api] %(message)s")

    key_store = APIKeyStore(storage_path=args.api_keys_path)
    limiter = RateLimiter()
    app = create_app(api_key_store=key_store, rate_limiter=limiter)

    logger.info("Starting Bantu-OS Network API on %s:%s", args.host, args.port)
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
