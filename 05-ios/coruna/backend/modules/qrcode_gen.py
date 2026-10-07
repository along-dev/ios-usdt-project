"""
QR Code Generator Module.
Generates QR codes for the landing page URL.
"""

from __future__ import annotations

import html
import io
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .server_urls import landing_page_url, qrcode_library_available

router = APIRouter(tags=["QR Code"])

_SAFE_URL = re.compile(r"^https?://[^\s<>'\"]+$", re.I)


def _normalize_qr_url(url: str) -> str:
    url = url.strip()
    if not _SAFE_URL.match(url):
        raise HTTPException(status_code=400, detail="Invalid URL for QR code")
    return url


def _generate_qr_svg(data: str, box_size: int = 10) -> str:
    """Generate QR code as inline SVG."""
    try:
        import qrcode
        import qrcode.image.svg

        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(image_factory=factory)
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode("utf-8")
    except ImportError:
        return _generate_qr_svg_fallback(data)


def _generate_qr_svg_fallback(data: str) -> str:
    """Minimal fallback when qrcode library is not installed."""
    safe = html.escape(data[:120], quote=True)
    size = 200
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
        f'<rect width="{size}" height="{size}" fill="white"/>',
        f'<text x="50%" y="40%" text-anchor="middle" font-family="monospace" font-size="10" fill="#333">Scan URL:</text>',
        f'<text x="50%" y="55%" text-anchor="middle" font-family="monospace" font-size="8" fill="#0066cc">{safe}</text>',
        f'<text x="50%" y="70%" text-anchor="middle" font-family="monospace" font-size="8" fill="#999">pip install qrcode</text>',
        "</svg>",
    ]
    return "\n".join(lines)


@router.get("/api/qrcode/status", summary="QR generator health")
async def qrcode_status():
    available = qrcode_library_available()
    return {
        "code": 0,
        "data": {
            "qrcode_installed": available,
            "degraded": not available,
            "hint": None if available else "Run: pip install 'qrcode[pil]>=7.4'",
        },
    }


@router.get("/api/qrcode", summary="Generate QR code for landing page")
async def generate_qrcode(request: Request, url: Optional[str] = None, format: str = "svg"):
    """
    Generate a QR code for the landing page URL.
    If no URL is provided, uses configured PUBLIC_BASE_URL or request Host.
    """
    if not url:
        url = landing_page_url(request)
    else:
        url = _normalize_qr_url(url)

    if format == "png":
        if not qrcode_library_available():
            return JSONResponse(
                {"code": 1, "msg": "qrcode library not installed. Run: pip install 'qrcode[pil]>=7.4'"},
                status_code=500,
            )
        import qrcode

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    svg_content = _generate_qr_svg(url)
    degraded = not qrcode_library_available()
    headers = {"Cache-Control": "no-cache"}
    if degraded:
        headers["X-QR-Degraded"] = "true"
    return StreamingResponse(
        io.BytesIO(svg_content.encode("utf-8")),
        media_type="image/svg+xml",
        headers=headers,
    )


@router.get("/api/qrcode/url", summary="Get landing page URL for QR code")
async def get_qrcode_url(request: Request):
    url = landing_page_url(request)
    return {
        "code": 0,
        "data": {
            "url": url,
            "public_base_url": url.rsplit("/group.html", 1)[0],
            "qrcode_api": f"/api/qrcode?url={url}",
            "degraded": not qrcode_library_available(),
        },
    }
