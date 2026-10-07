"""
Real Visitor Tracking Module.
Receives device fingerprint data from the tracking script injected into group.html.
Persists to SQLite and broadcasts to Dashboard via SSE.
"""

from __future__ import annotations

import time
import uuid
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from .state import app_state, TelemetryEvent
from .database import save_visitor, get_visitors, get_visitor_count
from .notifications import notify_new_visitor

router = APIRouter(tags=["Visitor Tracking"])


def _parse_ios_version(ua: str) -> str:
    m = re.search(r"OS[_ ](\d+)[._](\d+)(?:[._](\d+))?", ua)
    if m:
        major, minor = m.group(1), m.group(2)
        patch = m.group(3) or "0"
        return f"iOS {major}.{minor}.{patch}"
    return ""


def _parse_device_model(ua: str) -> str:
    m = re.search(r"(iPhone|iPad|iPod)\d+,\d+", ua)
    if m:
        return m.group(0)
    if "iPhone" in ua:
        return "iPhone"
    if "iPad" in ua:
        return "iPad"
    return ""


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return ""


@router.post("/api/track", summary="Receive visitor tracking data")
async def track_visitor(request: Request):
    """
    Called by the tracking script injected into group.html.
    Collects real device information and persists it.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    ip = _client_ip(request)
    ua = request.headers.get("user-agent", "")
    visit_id = body.get("visit_id") or uuid.uuid4().hex[:16]

    visitor_data = {
        "visit_id": visit_id,
        "ip": ip,
        "user_agent": ua,
        "device_model": body.get("device_model") or _parse_device_model(ua),
        "ios_version": body.get("ios_version") or _parse_ios_version(ua),
        "screen_w": body.get("screen_w", 0),
        "screen_h": body.get("screen_h", 0),
        "language": body.get("language", ""),
        "platform": body.get("platform", ""),
        "referrer": body.get("referrer", ""),
        "page_url": body.get("page_url", ""),
        "fingerprint": body.get("fingerprint", ""),
        "extra": {
            "timezone": body.get("timezone", ""),
            "color_depth": body.get("color_depth", 0),
            "touch_points": body.get("touch_points", 0),
            "device_memory": body.get("device_memory", 0),
            "hardware_concurrency": body.get("hardware_concurrency", 0),
            "connection_type": body.get("connection_type", ""),
        },
        "created_at": time.time(),
    }

    save_visitor(visitor_data)

    app_state.blocked_today += 1

    event = TelemetryEvent(
        channel_code="web_tracker",
        device_version=visitor_data["ios_version"] or ua[:40],
        domain=visitor_data["page_url"] or "group.html",
        ip=ip,
        event_type="VISITOR_DETECTED",
    )
    app_state.telemetry_events.append(event)
    app_state.telemetry_counter += 1

    await app_state.broadcast_sse({
        "type": "visitor",
        "data": {
            "visit_id": visit_id,
            "ip": ip,
            "device_model": visitor_data["device_model"],
            "ios_version": visitor_data["ios_version"],
            "user_agent": ua[:80],
            "screen": f"{visitor_data['screen_w']}x{visitor_data['screen_h']}",
            "language": visitor_data["language"],
            "platform": visitor_data["platform"],
            "timestamp": visitor_data["created_at"],
        },
    })

    await app_state.broadcast_sse({
        "type": "telemetry",
        "data": {
            "id": event.id,
            "timestamp": event.timestamp,
            "channel_code": event.channel_code,
            "device_version": event.device_version,
            "domain": event.domain,
            "ip": ip,
            "event_type": event.event_type,
        },
    })

    await notify_new_visitor(visitor_data)

    return {"code": 0, "msg": "tracked", "visit_id": visit_id}


@router.get("/api/visitors", summary="List all visitors")
async def list_visitors(limit: int = 100, offset: int = 0):
    rows = get_visitors(limit, offset)
    total = get_visitor_count()
    return {"code": 0, "data": {"total": total, "visitors": rows}}


@router.get("/api/visitors/count", summary="Get visitor count")
async def visitor_count():
    return {"code": 0, "data": {"total": get_visitor_count()}}


@router.get("/api/track/pixel.gif", summary="Tracking pixel (1x1 GIF)")
async def tracking_pixel(request: Request):
    """
    1x1 transparent GIF tracking pixel.
    Works even when JavaScript is disabled.
    """
    ip = _client_ip(request)
    ua = request.headers.get("user-agent", "")
    visit_id = uuid.uuid4().hex[:16]

    visitor_data = {
        "visit_id": visit_id,
        "ip": ip,
        "user_agent": ua,
        "device_model": _parse_device_model(ua),
        "ios_version": _parse_ios_version(ua),
        "screen_w": 0,
        "screen_h": 0,
        "language": request.headers.get("accept-language", "")[:20],
        "platform": "",
        "referrer": request.headers.get("referer", ""),
        "page_url": "",
        "fingerprint": "",
        "extra": {},
        "created_at": time.time(),
    }
    save_visitor(visitor_data)
    app_state.blocked_today += 1

    await app_state.broadcast_sse({
        "type": "visitor",
        "data": {
            "visit_id": visit_id,
            "ip": ip,
            "device_model": visitor_data["device_model"],
            "ios_version": visitor_data["ios_version"],
            "user_agent": ua[:80],
            "screen": "—",
            "language": visitor_data["language"],
            "platform": "pixel",
            "timestamp": visitor_data["created_at"],
        },
    })

    gif_1x1 = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    return Response(content=gif_1x1, media_type="image/gif", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    })
