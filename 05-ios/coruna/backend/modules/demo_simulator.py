"""
Demo Simulator — Generates realistic attack-chain events for live demonstrations.

When activated, simulates:
  1. Devices visiting the landing page (L0 telemetry)
  2. Exploit chain progression (Stage1 → Stage2 → Stage3)
  3. Implant registration and heartbeat
  4. Data exfiltration results (keychain, contacts, location, screenshots)
  5. C2 command dispatch and acknowledgement

All events are pushed to the Dashboard via SSE in real time.
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid

from fastapi import APIRouter

from .console_crud import upsert_device_from_implant
from .state import (
    AppState,
    C2Command,
    ImplantSession,
    TelemetryEvent,
    app_state,
)

router = APIRouter(tags=["Demo Simulator"])

# ── Realistic Device Profiles ────────────────────────────────────────────────

DEVICE_PROFILES = [
    {"model": "iPhone14,2", "name": "iPhone 13 Pro", "ios": "iOS 17.1.2", "ip": "172.16.8.42", "carrier": "中国移动"},
    {"model": "iPhone15,3", "name": "iPhone 14 Pro Max", "ios": "iOS 16.6.1", "ip": "10.0.12.88", "carrier": "中国联通"},
    {"model": "iPhone13,4", "name": "iPhone 12 Pro Max", "ios": "iOS 15.7.9", "ip": "192.168.3.107", "carrier": "中国电信"},
    {"model": "iPhone14,5", "name": "iPhone 13", "ios": "iOS 17.2.1", "ip": "10.8.0.56", "carrier": "AT&T"},
    {"model": "iPhone15,2", "name": "iPhone 14 Pro", "ios": "iOS 16.5.1", "ip": "172.20.1.203", "carrier": "Vodafone"},
    {"model": "iPhone12,1", "name": "iPhone 11", "ios": "iOS 16.1.2", "ip": "192.168.1.89", "carrier": "SoftBank"},
]

DOMAINS = [
    "cdn-apple.security.io",
    "verify.icloud-cdn.com",
    "api.telemetry.run",
    "hook.payload.net",
    "c2.secure-relay.io",
    "update.webkit-patch.com",
]

CHANNELS = ["ch_appstore_01", "ch_safari_02", "ch_deeplink_03", "ch_push_04", "ch_qr_05", "ch_sms_06"]

# Simulated exfiltrated data
KEYCHAIN_DATA = [
    {"service": "com.apple.wifi.known-networks", "account": "HomeWiFi-5G", "data": "WPA2:K8x#mP2$vQ9"},
    {"service": "com.apple.account.AppleID", "account": "user@icloud.com", "data": "********"},
    {"service": "com.apple.account.Google", "account": "user.test@gmail.com", "data": "********"},
    {"service": "com.tencent.xin (WeChat)", "account": "wxid_a8k2m9v3", "data": "token:eyJ0eXAi..."},
    {"service": "com.apple.wifi.known-networks", "account": "Starbucks_Free", "data": "OPEN"},
    {"service": "com.alipay.iphoneclient", "account": "138****5520", "data": "session:s%3A..."},
]

CONTACTS_DATA = [
    {"name": "张三", "phone": "+86 138****5520", "email": "zhangsan@example.com"},
    {"name": "李四", "phone": "+86 186****9912", "email": "lisi@company.cn"},
    {"name": "王五", "phone": "+86 159****3308", "email": ""},
    {"name": "Mom", "phone": "+86 135****7766", "email": ""},
    {"name": "Boss Chen", "phone": "+86 189****4455", "email": "chen@corp.com"},
]

LOCATION_DATA = [
    {"lat": 39.9042, "lon": 116.4074, "city": "北京市朝阳区", "accuracy": "10m"},
    {"lat": 31.2304, "lon": 121.4737, "city": "上海市浦东新区", "accuracy": "15m"},
    {"lat": 22.5431, "lon": 114.0579, "city": "深圳市南山区", "accuracy": "8m"},
]

SAFARI_HISTORY = [
    {"url": "https://www.apple.com/iphone", "title": "iPhone - Apple", "ts": "2026-07-21 14:30"},
    {"url": "https://mail.google.com", "title": "Gmail", "ts": "2026-07-21 15:12"},
    {"url": "https://bank.icbc.com.cn", "title": "工商银行", "ts": "2026-07-22 09:45"},
    {"url": "https://weixin.qq.com", "title": "微信网页版", "ts": "2026-07-22 10:20"},
]

# ── Simulation State ─────────────────────────────────────────────────────────

_sim_task: asyncio.Task | None = None
_sim_running = False


async def _run_simulation():
    """Main simulation loop that generates realistic attack-chain events."""
    global _sim_running
    _sim_running = True
    state = app_state

    try:
        # ── Phase 1: Telemetry flood (devices visiting landing page) ─────
        await state.broadcast_sse({
            "type": "demo_phase",
            "data": {"phase": 1, "title": "L0 投放页遥测涌入", "description": "目标设备正在访问投放页..."},
        })
        await asyncio.sleep(1.5)

        for i in range(8):
            if not _sim_running:
                return
            profile = random.choice(DEVICE_PROFILES)
            domain = random.choice(DOMAINS)
            channel = random.choice(CHANNELS)
            event = TelemetryEvent(
                channel_code=channel,
                device_version=profile["ios"],
                domain=domain,
                ip=profile["ip"],
                event_type=random.choice(["DEVICE_FINGERPRINT", "BEACON_PING"]),
            )
            await state.broadcast_sse({
                "type": "demo_telemetry",
                "data": {
                    "simulated": True,
                    "id": event.id,
                    "timestamp": event.timestamp,
                    "channel_code": event.channel_code,
                    "device_version": event.device_version,
                    "domain": event.domain,
                    "ip": event.ip,
                    "event_type": event.event_type,
                },
            })
            await asyncio.sleep(random.uniform(0.4, 1.2))

        elapsed_h = max((time.time() - state.start_time) / 3600, 0.01)
        state.layers["L1"].metrics["events_per_hour"] = int(state.telemetry_counter / elapsed_h)
        await state.broadcast_layer_update("L1")

        # ── Phase 2: Exploit chain execution on 3 devices ────────────────
        await state.broadcast_sse({
            "type": "demo_phase",
            "data": {"phase": 2, "title": "利用链执行中", "description": "Stage1 → Stage2 → Stage3 沙箱逃逸..."},
        })
        await asyncio.sleep(1)

        exploit_stages = [
            ("PAYLOAD_FETCH", "Stage1 WASM 内存原语加载"),
            ("SANDBOX_ESCAPE", "Stage2 PAC 绕过成功"),
            ("HOOK_INJECT", "Stage3 沙箱逃逸 · bootstrap.dylib 注入"),
            ("DYLIB_LOAD", "entry0 主植入物加载到 powerd"),
            ("ENTITLEMENT_CHECK", "权限提升完成 · 持久化安装"),
        ]

        compromised_devices = random.sample(DEVICE_PROFILES, min(3, len(DEVICE_PROFILES)))

        for device in compromised_devices:
            if not _sim_running:
                return
            for etype, _desc in exploit_stages:
                event = TelemetryEvent(
                    channel_code=f"exploit:{device['model']}",
                    device_version=device["ios"],
                    domain="c2.secure-relay.io",
                    ip=device["ip"],
                    event_type=etype,
                )
                await state.broadcast_sse({
                    "type": "demo_telemetry",
                    "data": {
                        "simulated": True,
                        "id": event.id,
                        "timestamp": event.timestamp,
                        "channel_code": event.channel_code,
                        "device_version": event.device_version,
                        "domain": event.domain,
                        "ip": event.ip,
                        "event_type": event.event_type,
                    },
                })
                await asyncio.sleep(random.uniform(0.3, 0.8))
            await asyncio.sleep(0.5)

        # ── Phase 3: Implant registration ────────────────────────────────
        await state.broadcast_sse({
            "type": "demo_phase",
            "data": {"phase": 3, "title": "植入物上线", "description": "目标设备注册到 C2 控制器..."},
        })
        await asyncio.sleep(1)

        sessions = []
        for device in compromised_devices:
            if not _sim_running:
                return
            session = ImplantSession(
                device_id=f"{device['model']}-{uuid.uuid4().hex[:6].upper()}",
                ip=device["ip"],
                ios_version=device["ios"],
            )
            sessions.append(session)
            upsert_device_from_implant(
                device_id=session.device_id,
                session_id=session.session_id,
                ip=device["ip"],
                ios_version=device["ios"],
                name=device["name"],
            )

            await state.broadcast_sse({
                "type": "demo_implant_register",
                "data": {
                    "simulated": True,
                    "session_id": session.session_id,
                    "device_id": session.device_id,
                    "ip": device["ip"],
                    "ios_version": device["ios"],
                    "model_name": device["name"],
                    "carrier": device["carrier"],
                },
            })
            await asyncio.sleep(random.uniform(1.0, 2.0))

        await state.broadcast_layer_update("L3")

        # ── Phase 4: Data exfiltration ───────────────────────────────────
        await state.broadcast_sse({
            "type": "demo_phase",
            "data": {"phase": 4, "title": "数据回传中", "description": "正在提取目标设备敏感数据..."},
        })
        await asyncio.sleep(1.5)

        for session in sessions:
            if not _sim_running:
                return
            device = next((d for d in compromised_devices if session.ip == d["ip"]), compromised_devices[0])

            # Keychain dump
            kc_sample = random.sample(KEYCHAIN_DATA, min(3, len(KEYCHAIN_DATA)))
            await state.broadcast_sse({
                "type": "demo_exfil_result",
                "data": {
                    "simulated": True,
                    "session_id": session.session_id,
                    "device_id": session.device_id,
                    "device_name": device["name"],
                    "exfil_type": "keychain",
                    "title": "Keychain 凭据提取",
                    "count": len(kc_sample),
                    "items": kc_sample,
                },
            })
            await asyncio.sleep(random.uniform(1.5, 2.5))

            # Contacts
            ct_sample = random.sample(CONTACTS_DATA, min(3, len(CONTACTS_DATA)))
            await state.broadcast_sse({
                "type": "demo_exfil_result",
                "data": {
                    "simulated": True,
                    "session_id": session.session_id,
                    "device_id": session.device_id,
                    "device_name": device["name"],
                    "exfil_type": "contacts",
                    "title": "通讯录提取",
                    "count": len(ct_sample),
                    "items": ct_sample,
                },
            })
            await asyncio.sleep(random.uniform(1.0, 2.0))

            # Location
            loc = random.choice(LOCATION_DATA)
            await state.broadcast_sse({
                "type": "demo_exfil_result",
                "data": {
                    "simulated": True,
                    "session_id": session.session_id,
                    "device_id": session.device_id,
                    "device_name": device["name"],
                    "exfil_type": "location",
                    "title": "实时定位获取",
                    "count": 1,
                    "items": [loc],
                },
            })
            await asyncio.sleep(random.uniform(1.0, 1.5))

            # Safari history
            await state.broadcast_sse({
                "type": "demo_exfil_result",
                "data": {
                    "simulated": True,
                    "session_id": session.session_id,
                    "device_id": session.device_id,
                    "device_name": device["name"],
                    "exfil_type": "safari_history",
                    "title": "Safari 浏览历史",
                    "count": len(SAFARI_HISTORY),
                    "items": SAFARI_HISTORY,
                },
            })
            await asyncio.sleep(random.uniform(1.0, 2.0))

        # ── Phase 5: C2 command dispatch ─────────────────────────────────
        await state.broadcast_sse({
            "type": "demo_phase",
            "data": {"phase": 5, "title": "远程指令下发", "description": "向已控设备下发控制指令..."},
        })
        await asyncio.sleep(1.5)

        demo_commands = [
            {"cmd": "screenshot", "args": {}, "result": {"status": "captured", "size": "2.4MB", "resolution": "2796x1290"}},
            {"cmd": "keychain", "args": {"filter": "com.apple.wifi"}, "result": {"entries": 12, "networks": ["HomeWiFi-5G", "Office_Corp", "Starbucks"]}},
            {"cmd": "hook_check", "args": {}, "result": {"hooked": ["launchd", "powerd", "CloudKeychainProxy"], "clean": ["locationd", "bluetoothd"]}},
        ]

        for cmd_info in demo_commands:
            if not _sim_running:
                return
            target = random.choice(sessions)
            cmd = C2Command(cmd=cmd_info["cmd"], args=cmd_info["args"], status="dispatched")
            state.command_history.append(cmd)

            await state.broadcast_sse({
                "type": "demo_command_dispatch",
                "data": {
                    "command_id": cmd.id,
                    "cmd": cmd.cmd,
                    "args": cmd.args,
                    "targets": [target.session_id],
                    "target_device": target.device_id,
                },
            })
            await asyncio.sleep(random.uniform(2.0, 3.0))

            cmd.status = "ack"
            cmd.response = cmd_info["result"]
            await state.broadcast_sse({
                "type": "demo_command_ack",
                "data": {
                    "command_id": cmd.id,
                    "session_id": target.session_id,
                    "device_id": target.device_id,
                    "cmd": cmd.cmd,
                    "status": "ack",
                    "result": cmd_info["result"],
                },
            })
            await asyncio.sleep(random.uniform(1.0, 2.0))

        # ── Phase 6: Complete ────────────────────────────────────────────
        await state.broadcast_sse({
            "type": "demo_phase",
            "data": {
                "phase": 6,
                "title": "演示完成",
                "description": f"演示完成 · 模拟控制 {len(sessions)} 台设备",
            },
        })

    finally:
        _sim_running = False


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/api/demo/start", summary="Start demo simulation")
async def start_demo():
    global _sim_task, _sim_running
    if _sim_running:
        return {"code": 1, "msg": "Demo already running"}
    _sim_task = asyncio.create_task(_run_simulation())
    return {"code": 0, "msg": "Demo simulation started"}


@router.post("/api/demo/stop", summary="Stop demo simulation")
async def stop_demo():
    global _sim_running, _sim_task
    _sim_running = False
    if _sim_task:
        _sim_task.cancel()
        _sim_task = None
    return {"code": 0, "msg": "Demo simulation stopped"}


@router.get("/api/demo/status", summary="Check demo simulation status")
async def demo_status():
    return {"code": 0, "data": {"running": _sim_running}}
