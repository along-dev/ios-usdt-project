"""
Hierarchical proxy management — parent agents see and manage descendant data.
"""

from __future__ import annotations

import secrets
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .audit import audit
from .auth import hash_password, require_admin, require_console_user
from .database import (
    delete_proxy,
    get_devices,
    get_proxy_by_channel,
    get_proxy_by_id,
    get_proxy_descendant_ids,
    get_proxy_tree,
    get_proxies,
    get_proxy_live_stats,
    save_proxy,
    save_user,
    get_user_by_username,
)

router = APIRouter(tags=["Proxy Hierarchy"])


class ProxyCreateIn(BaseModel):
    name: str
    parent_proxy_id: str = ""
    note: str = ""
    login_username: str = ""
    login_password: str = ""
    status: str = "active"


class ProxyUpdateIn(BaseModel):
    name: Optional[str] = None
    parent_proxy_id: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    login_password: Optional[str] = None


def _auth_scope(request: Request) -> dict[str, Any]:
    return require_console_user(request)


def _visible_proxy_ids(scope: dict[str, Any]) -> Optional[list[str]]:
    if scope.get("role") == "admin":
        return None
    proxy_id = scope.get("proxy_id", "")
    if not proxy_id:
        return []
    return get_proxy_descendant_ids(proxy_id)


def _ensure_proxy_access(scope: dict[str, Any], proxy_id: str) -> None:
    if scope.get("role") == "admin":
        return
    allowed = _visible_proxy_ids(scope) or []
    if proxy_id not in allowed:
        raise HTTPException(403, "Proxy out of scope")


def _proxy_out(row: dict, *, include_children: bool = False) -> dict:
    stats = get_proxy_live_stats(row["proxy_id"])
    out = {
        "id": row.get("proxy_id", ""),
        "proxy_id": row.get("proxy_id", ""),
        "name": row.get("name", ""),
        "parent_proxy_id": row.get("parent_proxy_id", ""),
        "channel_code": row.get("channel_code", ""),
        "login_username": row.get("login_username", ""),
        "deviceCount": stats["device_count"],
        "totalAssets": stats["total_assets_usd"],
        "status": row.get("status", "active"),
        "note": row.get("note", ""),
        "depth": row.get("depth", 0),
        "last_check_at": row.get("last_check_at", 0),
        "createdAt": time.strftime(
            "%Y-%m-%d",
            time.localtime(row.get("created_at", time.time())),
        ),
    }
    if include_children:
        out["children"] = [
            _proxy_out(child) for child in row.get("children", [])
        ]
    return out


@router.get("/api/proxies/tree", summary="Proxy hierarchy tree")
async def proxy_tree(request: Request):
    scope = _auth_scope(request)
    visible = _visible_proxy_ids(scope)
    if scope.get("role") == "proxy":
        root_id = scope.get("proxy_id", "")
        tree = get_proxy_tree(root_id=root_id, scope_ids=visible)
    else:
        tree = get_proxy_tree(scope_ids=visible)
    flat = []
    stats_total_devices = 0
    stats_total_assets = 0.0

    def walk(nodes: list[dict], depth: int = 0):
        for node in nodes:
            node["depth"] = depth
            item = _proxy_out(node)
            flat.append(item)
            nonlocal stats_total_devices, stats_total_assets
            stats_total_devices += item["deviceCount"]
            stats_total_assets += item["totalAssets"]
            walk(node.get("children", []), depth + 1)

    walk(tree)
    return {
        "code": 0,
        "data": {
            "tree": [_proxy_out(n, include_children=True) for n in tree],
            "proxies": flat,
            "stats": {
                "count": len(flat),
                "total_devices": stats_total_devices,
                "total_assets": round(stats_total_assets, 2),
            },
            "scope": {
                "role": scope.get("role"),
                "proxy_id": scope.get("proxy_id", ""),
            },
        },
    }


@router.get("/api/proxies/{proxy_id}/detail", summary="Proxy detail with devices")
async def proxy_detail(proxy_id: str, request: Request):
    scope = _auth_scope(request)
    _ensure_proxy_access(scope, proxy_id)
    row = get_proxy_by_id(proxy_id)
    if not row:
        raise HTTPException(404, "Proxy not found")
    subtree = get_proxy_descendant_ids(proxy_id)
    devices = get_devices(proxy_ids=subtree)
    stats = get_proxy_live_stats(proxy_id)
    return {
        "code": 0,
        "data": {
            "proxy": _proxy_out(row),
            "stats": stats,
            "devices": devices,
            "child_proxy_ids": [p for p in subtree if p != proxy_id],
        },
    }


@router.post("/api/proxies/hierarchy", summary="Create proxy with login account")
async def create_proxy_hierarchy(body: ProxyCreateIn, request: Request):
    require_admin(request)
    parent_id = body.parent_proxy_id.strip()
    if parent_id and not get_proxy_by_id(parent_id):
        raise HTTPException(400, "Parent proxy not found")

    proxy_id = f"PX-{uuid.uuid4().hex[:8]}"
    channel_code = secrets.token_hex(4).upper()
    login_username = body.login_username.strip() or f"proxy_{proxy_id.lower()}"
    login_password = body.login_password.strip() or secrets.token_urlsafe(10)

    if get_user_by_username(login_username):
        raise HTTPException(400, "Login username already exists")

    now = time.time()
    save_proxy({
        "proxy_id": proxy_id,
        "name": body.name,
        "parent_proxy_id": parent_id,
        "channel_code": channel_code,
        "login_username": login_username,
        "status": body.status,
        "note": body.note,
        "device_count": 0,
        "total_assets": 0,
        "last_check_at": now,
        "created_at": now,
    })
    save_user({
        "username": login_username,
        "password_hash": hash_password(login_password),
        "role": "proxy",
        "proxy_id": proxy_id,
    })
    audit("create_proxy", f"proxy:{proxy_id}", detail=f"parent={parent_id or 'root'}")
    return {
        "code": 0,
        "data": {
            "proxy_id": proxy_id,
            "channel_code": channel_code,
            "login_username": login_username,
            "login_password": login_password,
            "invite_url_hint": f"group.html?channel={channel_code}",
        },
    }


@router.put("/api/proxies/{proxy_id}/hierarchy", summary="Update proxy in hierarchy")
async def update_proxy_hierarchy(proxy_id: str, body: ProxyUpdateIn, request: Request):
    scope = _auth_scope(request)
    _ensure_proxy_access(scope, proxy_id)
    row = get_proxy_by_id(proxy_id)
    if not row:
        raise HTTPException(404, "Proxy not found")

    if body.parent_proxy_id is not None and scope.get("role") != "admin":
        raise HTTPException(403, "Only admin can change parent proxy")

    if body.parent_proxy_id:
        if body.parent_proxy_id == proxy_id:
            raise HTTPException(400, "Proxy cannot be its own parent")
        descendants = get_proxy_descendant_ids(proxy_id)
        if body.parent_proxy_id in descendants:
            raise HTTPException(400, "Cannot move proxy under its descendant")
        if not get_proxy_by_id(body.parent_proxy_id):
            raise HTTPException(400, "Parent proxy not found")

    for key, val in body.model_dump(exclude_unset=True).items():
        if key == "login_password":
            continue
        if val is not None:
            row[key] = val

    save_proxy(row)

    if body.login_password:
        username = row.get("login_username", "")
        if username:
            save_user({
                "username": username,
                "password_hash": hash_password(body.login_password),
                "role": "proxy",
                "proxy_id": proxy_id,
            })

    audit("update_proxy", f"proxy:{proxy_id}", detail=f"by={scope.get('sub')}")
    return {"code": 0, "data": _proxy_out(row)}


@router.delete("/api/proxies/{proxy_id}/hierarchy", summary="Delete proxy subtree root")
async def delete_proxy_hierarchy(proxy_id: str, request: Request):
    scope = _auth_scope(request)
    if scope.get("role") != "admin":
        _ensure_proxy_access(scope, proxy_id)
    row = get_proxy_by_id(proxy_id)
    if not row:
        raise HTTPException(404, "Proxy not found")
    descendants = get_proxy_descendant_ids(proxy_id)
    for pid in reversed(descendants):
        prow = get_proxy_by_id(pid)
        if prow and prow.get("login_username"):
            from .database import delete_user_by_username
            delete_user_by_username(prow["login_username"])
        delete_proxy(pid)
    audit("delete_proxy", f"proxy:{proxy_id}", detail=f"removed={len(descendants)}")
    return {"code": 0, "msg": "deleted", "data": {"removed": len(descendants)}}


@router.get("/api/proxies/channel/{channel_code}", summary="Resolve proxy channel (public)")
async def resolve_channel(channel_code: str):
    row = get_proxy_by_channel(channel_code.upper())
    if not row:
        raise HTTPException(404, "Unknown channel")
    return {
        "code": 0,
        "data": {
            "proxy_id": row["proxy_id"],
            "name": row["name"],
            "channel_code": row["channel_code"],
        },
    }
