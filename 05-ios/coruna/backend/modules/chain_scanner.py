"""
On-chain balance scanner — catalog-driven queries for all COLLECT_ASSETS.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from .collect_catalog import COLLECT_ASSETS, WALLET_KEYS, compute_row_total_usd
from .database import (
    get_device_asset_rows_for_scan,
    get_device_assets,
    get_rpc_settings,
    save_device_assets,
)

logger = logging.getLogger(__name__)


def _pad_eth_address(address: str) -> str:
    addr = address.lower().replace("0x", "")
    return addr.rjust(64, "0")


async def fetch_evm_erc20(rpc_url: str, contract: str, address: str, decimals: int) -> float:
    if not rpc_url or not contract or not address:
        return 0.0
    data = "0x70a08231" + _pad_eth_address(address)
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": contract, "data": data}, "latest"],
        "id": 1,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(rpc_url, json=payload)
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise RuntimeError(str(body["error"]))
        result = body.get("result", "0x0")
        raw = int(result, 16) if result and result != "0x" else 0
        return raw / (10 ** decimals)


async def fetch_evm_native(rpc_url: str, address: str, decimals: int = 18) -> float:
    if not rpc_url or not address:
        return 0.0
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [address, "latest"],
        "id": 1,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(rpc_url, json=payload)
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise RuntimeError(str(body["error"]))
        result = body.get("result", "0x0")
        raw = int(result, 16) if result and result != "0x" else 0
        return raw / (10 ** decimals)


async def fetch_trx_usdt_balance(rpc_url: str, contract: str, address: str, decimals: int = 6) -> float:
    if not rpc_url or not address:
        return 0.0
    base = rpc_url.rstrip("/")
    url = f"{base}/v1/accounts/{address}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data") or []
        if not data:
            return 0.0
        trc20_list = data[0].get("trc20") or []
        for item in trc20_list:
            if not isinstance(item, dict):
                continue
            for key, val in item.items():
                if key == contract or key.lower() == contract.lower():
                    return int(val) / (10 ** decimals)
        return 0.0


async def fetch_trx_native(rpc_url: str, address: str, decimals: int = 6) -> float:
    if not rpc_url or not address:
        return 0.0
    base = rpc_url.rstrip("/")
    url = f"{base}/v1/accounts/{address}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data") or []
        if not data:
            return 0.0
        return int(data[0].get("balance", 0) or 0) / (10 ** decimals)


async def fetch_btc_balance(btc_api: str, address: str) -> float:
    if not btc_api or not address:
        return 0.0
    base = btc_api.rstrip("/")
    url = f"{base}/address/{address}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        body = resp.json()
        stats = body.get("chain_stats") or {}
        funded = int(stats.get("funded_txo_sum", 0))
        spent = int(stats.get("spent_txo_sum", 0))
        mempool = body.get("mempool_stats") or {}
        mf = int(mempool.get("funded_txo_sum", 0))
        ms = int(mempool.get("spent_txo_sum", 0))
        sats = (funded - spent) + (mf - ms)
        return max(0, sats) / 1e8


async def fetch_sol_spl_balance(
    rpc_url: str,
    owner: str,
    mint: str,
    decimals: int = 6,
) -> float:
    if not rpc_url or not owner or not mint:
        return 0.0
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            owner,
            {"mint": mint},
            {"encoding": "jsonParsed"},
        ],
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(rpc_url, json=payload)
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise RuntimeError(str(body["error"]))
        total = 0.0
        for item in body.get("result", {}).get("value", []):
            info = item.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
            token_amount = info.get("tokenAmount", {})
            total += float(token_amount.get("uiAmount", 0) or 0)
        return total


async def fetch_sol_native(rpc_url: str, address: str, decimals: int = 9) -> float:
    if not rpc_url or not address:
        return 0.0
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [address],
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(rpc_url, json=payload)
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise RuntimeError(str(body["error"]))
        lamports = body.get("result", {}).get("value", 0)
        return int(lamports) / (10 ** decimals)


def _contract_for_asset(asset: dict[str, Any], rpc: dict[str, str]) -> str:
    if asset.get("contract"):
        return asset["contract"]
    key = asset.get("contract_key")
    if key:
        return rpc.get(key, "")
    return ""


async def scan_asset_balance(
    asset: dict[str, Any],
    row: dict[str, Any],
    rpc: dict[str, str],
) -> tuple[Optional[float], Optional[str]]:
    wallet = row.get(asset["wallet_key"], "")
    if not wallet:
        return None, None
    rpc_url = rpc.get(asset["rpc"], "")
    if not rpc_url:
        return None, f"{asset['id']}: RPC not configured"

    chain = asset["chain"]
    decimals = int(asset.get("decimals", 6))
    try:
        if chain == "BTC":
            return await fetch_btc_balance(rpc_url, wallet), None
        if chain == "TRX":
            if asset.get("native"):
                return await fetch_trx_native(rpc_url, wallet, decimals), None
            contract = _contract_for_asset(asset, rpc)
            return await fetch_trx_usdt_balance(rpc_url, contract, wallet, decimals), None
        if chain in ("ETH", "BSC"):
            if asset.get("native"):
                return await fetch_evm_native(rpc_url, wallet, decimals), None
            contract = _contract_for_asset(asset, rpc)
            return await fetch_evm_erc20(rpc_url, contract, wallet, decimals), None
        if chain == "SOL":
            if asset.get("native"):
                return await fetch_sol_native(rpc_url, wallet, decimals), None
            contract = _contract_for_asset(asset, rpc)
            val = await fetch_sol_spl_balance(rpc_url, wallet, contract, decimals)
            return val, None
    except Exception as exc:
        return None, f"{asset['id']}: {exc}"
    return None, f"{asset['id']}: unsupported"


async def scan_device_balances(device_id: str, rpc: Optional[dict] = None) -> dict[str, Any]:
    rpc = rpc or get_rpc_settings()
    rows = get_device_asset_rows_for_scan(device_id)
    if not rows:
        existing = get_device_assets(device_id) or {"device_id": device_id}
        return {
            "device_id": device_id,
            "ok": False,
            "error": "Device has no wallet addresses — wait for implant wallet report",
            **existing,
        }

    row = rows[0]
    errors: list[str] = []
    balances: dict[str, float] = {}

    for asset in COLLECT_ASSETS:
        key = asset["balance_key"]
        existing = float(row.get(key, 0) or 0)
        val, err = await scan_asset_balance(asset, row, rpc)
        if err:
            errors.append(err)
            if val is not None:
                balances[key] = val
            else:
                balances[key] = existing
        elif val is not None:
            balances[key] = val
        else:
            balances[key] = existing

    wallet_count = sum(1 for wk in WALLET_KEYS if row.get(wk))
    scan_error = "; ".join(errors)
    any_balance = any(v > 0 for v in balances.values())
    status = "ready" if not errors else ("partial" if any_balance else "error")

    now = time.time()
    payload: dict[str, Any] = {
        "device_id": device_id,
        "wallet_count": wallet_count,
        "status": status,
        "source": "rpc",
        "scan_error": scan_error,
        "last_scan_at": now,
        "updated_at": now,
    }
    for wk in WALLET_KEYS:
        payload[wk] = row.get(wk, "")
    payload.update(balances)
    payload["total_usd"] = compute_row_total_usd({**row, **balances})

    save_device_assets(payload)
    return {"ok": not errors, "error": scan_error, **payload}


async def scan_all_device_balances() -> dict[str, Any]:
    rows = get_device_asset_rows_for_scan()
    rpc = get_rpc_settings()
    results = []
    for row in rows:
        try:
            results.append(await scan_device_balances(row["device_id"], rpc))
        except Exception as exc:
            logger.exception("scan failed for %s", row["device_id"])
            results.append({"device_id": row["device_id"], "ok": False, "error": str(exc)})
    ok_count = sum(1 for r in results if r.get("ok"))
    return {
        "scanned": len(results),
        "success": ok_count,
        "failed": len(results) - ok_count,
        "results": results,
    }


async def test_rpc_connections(rpc: Optional[dict] = None) -> dict[str, Any]:
    rpc = rpc or get_rpc_settings()
    checks: dict[str, Any] = {}

    async def _evm_ping(name: str, url: str) -> None:
        if not url:
            checks[name] = {"ok": False, "detail": "not configured"}
            return
        try:
            payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                block = resp.json().get("result")
                checks[name] = {"ok": bool(block), "detail": f"block={block}"}
        except Exception as exc:
            checks[name] = {"ok": False, "detail": str(exc)}

    await _evm_ping("eth", rpc.get("eth_rpc", ""))
    await _evm_ping("bsc", rpc.get("bsc_rpc", ""))

    if rpc.get("trx_rpc"):
        try:
            base = rpc["trx_rpc"].rstrip("/")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{base}/wallet/getnowblock")
                checks["trx"] = {"ok": resp.status_code == 200, "detail": f"HTTP {resp.status_code}"}
        except Exception as exc:
            checks["trx"] = {"ok": False, "detail": str(exc)}
    else:
        checks["trx"] = {"ok": False, "detail": "not configured"}

    if rpc.get("btc_api"):
        try:
            base = rpc["btc_api"].rstrip("/")
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{base}/blocks/tip/height")
                checks["btc"] = {"ok": resp.status_code == 200, "detail": resp.text.strip()[:32]}
        except Exception as exc:
            checks["btc"] = {"ok": False, "detail": str(exc)}
    else:
        checks["btc"] = {"ok": False, "detail": "not configured"}

    if rpc.get("sol_rpc"):
        try:
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getHealth"}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(rpc["sol_rpc"], json=payload)
                checks["sol"] = {"ok": resp.status_code == 200, "detail": resp.text[:40]}
        except Exception as exc:
            checks["sol"] = {"ok": False, "detail": str(exc)}
    else:
        checks["sol"] = {"ok": False, "detail": "not configured"}

    return checks
