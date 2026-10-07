"""
Audit log — records sensitive console actions.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from .auth import require_admin
from .database import get_audit_log, write_audit_log

router = APIRouter(tags=["Audit"])


def audit(action: str, resource: str, who: str = "admin", detail: str = "") -> None:
    write_audit_log({
        "who": who,
        "action": action,
        "resource": resource,
        "detail": detail,
    })


@router.get("/api/audit", summary="Audit log (admin)")
async def list_audit(request: Request, limit: int = 100):
    require_admin(request)
    rows = get_audit_log(limit=limit)
    return {"code": 0, "data": rows}
