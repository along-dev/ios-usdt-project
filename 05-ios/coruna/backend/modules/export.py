"""
Data Export Module.
Provides CSV and JSON export for visitors and telemetry events.
"""

from __future__ import annotations

import csv
import io
import json
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse

from .database import export_visitors_all, export_telemetry_all

router = APIRouter(tags=["Data Export"])


def _timestamp_str() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


@router.get("/api/export/visitors", summary="Export all visitors")
async def export_visitors(format: str = "json"):
    rows = export_visitors_all()

    if format == "csv":
        if not rows:
            return StreamingResponse(
                io.StringIO("No data\n"),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=visitors_{_timestamp_str()}.csv"},
            )
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=visitors_{_timestamp_str()}.csv"},
        )

    return JSONResponse(
        content={"code": 0, "count": len(rows), "data": rows},
        headers={"Content-Disposition": f"attachment; filename=visitors_{_timestamp_str()}.json"},
    )


@router.get("/api/export/telemetry", summary="Export all telemetry events")
async def export_telemetry(format: str = "json"):
    rows = export_telemetry_all()

    if format == "csv":
        if not rows:
            return StreamingResponse(
                io.StringIO("No data\n"),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=telemetry_{_timestamp_str()}.csv"},
            )
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=telemetry_{_timestamp_str()}.csv"},
        )

    return JSONResponse(
        content={"code": 0, "count": len(rows), "data": rows},
        headers={"Content-Disposition": f"attachment; filename=telemetry_{_timestamp_str()}.json"},
    )
