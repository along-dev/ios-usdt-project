"""
Dynamic daemon hook matrix — updated from implant hook_check responses.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .auth import require_tweak_or_admin
from .state import (
    AppState,
    DaemonHookEntry,
    DylibStatus,
    HookRisk,
    app_state,
)

router = APIRouter(tags=["Daemon Hooks"])


class HookReportBody(BaseModel):
    process: str = ""
    pid: int = 0
    inject_target: str = Field("", alias="target")
    dylib_path: str = ""
    dylib_name: str = ""
    risk: str = "medium"
    hooks: list[dict] = Field(default_factory=list)

    class Config:
        extra = "allow"
        populate_by_name = True


def _risk_from_string(val: str) -> HookRisk:
    val = (val or "").lower()
    if val in ("high", "critical"):
        return HookRisk.HIGH
    if val in ("medium", "med", "warning"):
        return HookRisk.MEDIUM
    return HookRisk.LOW


def _dylib_status_from_string(val: str) -> DylibStatus:
    val = (val or "").lower()
    if val in ("detected", "hooked", "injected"):
        return DylibStatus.DETECTED
    if val in ("suspicious", "unknown"):
        return DylibStatus.SUSPICIOUS
    return DylibStatus.CLEAN


def hook_entry_to_dict(entry: DaemonHookEntry) -> dict:
    return {
        "process": entry.process,
        "pid": entry.pid,
        "inject_target": entry.inject_target,
        "risk": entry.risk.value,
        "dylib_status": entry.dylib_status.value,
        "dylib_name": entry.dylib_name,
        "source": getattr(entry, "source", "static"),
    }


def apply_hook_report(report: dict, source: str = "implant") -> None:
    """Merge hook_check payload into the daemon hook matrix."""
    hooks = report.get("hooks") or report.get("processes") or []
    if isinstance(report, list):
        hooks = report
    if not hooks and report.get("process"):
        hooks = [report]

    for item in hooks:
        if not isinstance(item, dict):
            continue
        process = item.get("process") or item.get("name") or ""
        if not process:
            continue
        entry = DaemonHookEntry(
            process=process,
            pid=int(item.get("pid", 0) or 0),
            inject_target=item.get("inject_target") or item.get("target") or "",
            risk=_risk_from_string(item.get("risk", "low")),
            dylib_status=_dylib_status_from_string(
                item.get("dylib_status") or item.get("dylib") or "clean"
            ),
            dylib_name=item.get("dylib_name") or item.get("dylibName") or "—",
        )
        entry.source = source
        _upsert_hook(entry)


def _upsert_hook(entry: DaemonHookEntry) -> None:
    for i, existing in enumerate(app_state.daemon_hooks):
        if existing.process == entry.process:
            app_state.daemon_hooks[i] = entry
            return
    app_state.daemon_hooks.append(entry)


async def broadcast_hook_update(state: AppState = app_state) -> None:
    await state.broadcast_sse({
        "type": "daemon_hooks_update",
        "data": {"hooks": [hook_entry_to_dict(h) for h in state.daemon_hooks]},
    })


@router.post("/api/hooks/report", summary="Report daemon hooks from tweak/implant")
async def report_hooks(body: HookReportBody, request: Request):
    require_tweak_or_admin(request)
    payload = body.model_dump()
    if body.hooks:
        apply_hook_report({"hooks": body.hooks}, source="tweak")
    else:
        apply_hook_report({
            "process": body.process or "SpringBoard",
            "pid": body.pid,
            "inject_target": body.inject_target or body.dylib_path,
            "dylib_name": body.dylib_name or body.dylib_path or "tweak.dylib",
            "risk": body.risk,
            "dylib_status": "detected",
        }, source="tweak")
    await broadcast_hook_update()
    return {"code": 0, "msg": "hook report accepted"}


@router.get("/api/daemon-hooks", summary="Daemon hook matrix")
async def list_daemon_hooks():
    return {
        "code": 0,
        "data": [hook_entry_to_dict(h) for h in app_state.daemon_hooks],
    }
