"""
Shared in-memory state for the C2 simulation controller.
All modules read/write from this singleton to keep the full pipeline coherent.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LayerStatus(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    DOWN = "down"
    IDLE = "idle"


class HookRisk(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DylibStatus(str, Enum):
    DETECTED = "detected"
    SUSPICIOUS = "suspicious"
    CLEAN = "clean"


# ── Telemetry Event ──────────────────────────────────────────────────────────

@dataclass
class TelemetryEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    channel_code: str = ""
    device_version: str = ""
    domain: str = ""
    ip: str = ""
    event_type: str = "BEACON_PING"
    raw_body: dict = field(default_factory=dict)


# ── C2 Command ───────────────────────────────────────────────────────────────

@dataclass
class C2Command:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    cmd: str = ""
    args: dict = field(default_factory=dict)
    status: str = "pending"       # pending / dispatched / ack / error
    response: dict | None = None


# ── Implant Session ──────────────────────────────────────────────────────────

@dataclass
class ImplantSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    device_id: str = ""
    ip: str = ""
    ios_version: str = ""
    last_heartbeat: float = field(default_factory=time.time)
    is_alive: bool = True
    implant_token: str = ""
    command_queue: list[C2Command] = field(default_factory=list)


# ── Daemon Hook Entry ────────────────────────────────────────────────────────

@dataclass
class DaemonHookEntry:
    process: str = ""
    pid: int = 0
    inject_target: str = ""
    risk: HookRisk = HookRisk.LOW
    dylib_status: DylibStatus = DylibStatus.CLEAN
    dylib_name: str = "—"
    source: str = "static"


# ── Layer State ──────────────────────────────────────────────────────────────

@dataclass
class LayerState:
    layer_id: str = ""         # L0 / L1 / L2 / L3
    label: str = ""
    status: LayerStatus = LayerStatus.IDLE
    metrics: dict = field(default_factory=dict)


# ── Global Application State ────────────────────────────────────────────────

class AppState:
    """Singleton that holds ALL runtime state for the C2 simulation."""

    def __init__(self) -> None:
        # L1 telemetry ring buffer (last 10 000 events)
        self.telemetry_events: deque[TelemetryEvent] = deque(maxlen=10_000)
        self.telemetry_counter: int = 0

        # SSE subscriber queues — each connected dashboard gets one
        self.sse_subscribers: list[asyncio.Queue] = []

        # L2 payload manifest cache
        self.payload_manifest: dict[str, Any] | None = None
        self.payload_root: str = ""

        # Public URL for QR codes / landing links (set at server startup)
        self.public_base_url: str = ""
        self.server_port: int = 9000

        # L3 implant sessions
        self.implant_sessions: dict[str, ImplantSession] = {}
        self.command_history: deque[C2Command] = deque(maxlen=5_000)

        # Layer health
        self.layers: dict[str, LayerState] = {
            "L0": LayerState(
                layer_id="L0", label="投放页 · Landing",
                status=LayerStatus.ACTIVE,
                metrics={"domains": 12, "uptime": "99.9%", "latency_ms": 23},
            ),
            "L1": LayerState(
                layer_id="L1", label="遥测上报 · Telemetry",
                status=LayerStatus.ACTIVE,
                metrics={"events_per_hour": 0, "queue_depth": 0},
            ),
            "L2": LayerState(
                layer_id="L2", label="Payload CDN",
                status=LayerStatus.ACTIVE,
                metrics={"cache_hit": "0%", "cdn_nodes": "0/0"},
            ),
            "L3": LayerState(
                layer_id="L3", label="IPC/C2 模拟桩",
                status=LayerStatus.ACTIVE,
                metrics={"ipc_channels": 4, "c2_heartbeat": "OK"},
            ),
        }

        # Daemon hook matrix
        self.daemon_hooks: list[DaemonHookEntry] = [
            DaemonHookEntry("launchd", 1, "com.apple.xpc.launchd", HookRisk.HIGH, DylibStatus.DETECTED, "libsubstrate.dylib"),
            DaemonHookEntry("powerd", 89, "IOPMrootDomain", HookRisk.MEDIUM, DylibStatus.CLEAN, "—"),
            DaemonHookEntry("AppleCredentialManagerDaemon", 247, "SecKeychain.framework", HookRisk.HIGH, DylibStatus.DETECTED, "credhook.dylib"),
            DaemonHookEntry("CloudKeychainProxy", 312, "com.apple.security.cloudkeychainproxy", HookRisk.HIGH, DylibStatus.DETECTED, "kcproxyhook.dylib"),
            DaemonHookEntry("backupd", 156, "com.apple.backupd", HookRisk.MEDIUM, DylibStatus.SUSPICIOUS, "backupinject.dylib"),
            DaemonHookEntry("locationd", 78, "CoreLocation.framework", HookRisk.LOW, DylibStatus.CLEAN, "—"),
            DaemonHookEntry("bluetoothd", 95, "IOBluetooth.framework", HookRisk.LOW, DylibStatus.CLEAN, "—"),
            DaemonHookEntry("wifid", 102, "CoreWiFi.framework", HookRisk.MEDIUM, DylibStatus.SUSPICIOUS, "wifimon.dylib"),
            DaemonHookEntry("configd", 45, "SystemConfiguration.framework", HookRisk.LOW, DylibStatus.CLEAN, "—"),
            DaemonHookEntry("notifyd", 33, "com.apple.notifyd", HookRisk.LOW, DylibStatus.CLEAN, "—"),
        ]

        # Aggregate counters (hydrated from real events, not hard-coded demo values)
        self.blocked_today: int = 0
        self.captured_today: int = 0
        self.system_health: float = 100.0
        self.start_time: float = time.time()

        # L2 payload CDN request counter
        self.payload_requests: int = 0

        # Global control switches (loaded from SQLite on startup)
        self.global_control: dict[str, bool] = {
            "auto_collect": True,
            "silent": False,
            "heartbeat": True,
            "proxy_forward": False,
            "log_report": True,
            "controlled_filter": False,
        }

    # ── SSE helpers ──────────────────────────────────────────────────────

    async def broadcast_sse(self, event: dict) -> None:
        dead: list[int] = []
        for i, q in enumerate(self.sse_subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(i)
        for i in reversed(dead):
            self.sse_subscribers.pop(i)

    def subscribe_sse(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        self.sse_subscribers.append(q)
        return q

    def unsubscribe_sse(self, q: asyncio.Queue) -> None:
        try:
            self.sse_subscribers.remove(q)
        except ValueError:
            pass

    async def broadcast_layer_update(self, layer_id: str) -> None:
        layer = self.layers.get(layer_id)
        if not layer:
            return
        await self.broadcast_sse({
            "type": "layer_update",
            "data": {
                "layer_id": layer_id,
                "label": layer.label,
                "status": layer.status.value,
                "metrics": dict(layer.metrics),
            },
        })


# Module-level singleton
app_state = AppState()
