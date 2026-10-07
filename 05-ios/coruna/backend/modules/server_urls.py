"""Resolve public landing-page URLs for QR codes and console links."""

from __future__ import annotations

import socket

from fastapi import Request

from .state import app_state


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def configure_public_base_url(base_url: str = "", host: str = "0.0.0.0", port: int = 9000) -> str:
    """Set app_state.public_base_url from CLI flag or detected LAN address."""
    app_state.server_port = port
    base = (base_url or "").strip().rstrip("/")
    if base:
        app_state.public_base_url = base
        return base
    bind_ip = local_ip() if host in ("0.0.0.0", "::") else host
    app_state.public_base_url = f"http://{bind_ip}:{port}"
    return app_state.public_base_url


def landing_page_url(request: Request | None = None) -> str:
    """Prefer configured base URL, then reverse-proxy Host header, then defaults."""
    if app_state.public_base_url:
        return f"{app_state.public_base_url.rstrip('/')}/group.html"

    if request is not None:
        host = request.headers.get("host", "").strip()
        if host:
            scheme = request.headers.get("x-forwarded-proto", "http").split(",")[0].strip()
            return f"{scheme}://{host}/group.html"

    return f"http://{local_ip()}:{app_state.server_port}/group.html"


def qrcode_library_available() -> bool:
    try:
        import qrcode  # noqa: F401

        return True
    except ImportError:
        return False
