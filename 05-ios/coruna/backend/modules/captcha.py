"""
Simple SVG captcha for console login.
"""

from __future__ import annotations

import random
import secrets
import string
import time
from typing import Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Auth"])

_CAPTCHA_STORE: dict[str, dict] = {}
_CAPTCHA_TTL = 300
_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _purge_expired() -> None:
    now = time.time()
    expired = [k for k, v in _CAPTCHA_STORE.items() if v["expires_at"] < now]
    for key in expired:
        _CAPTCHA_STORE.pop(key, None)


def _generate_code(length: int = 5) -> str:
    return "".join(random.choice(_CHARS) for _ in range(length))


def _svg_for_code(code: str) -> str:
    width, height = 140, 48
    noise = "".join(
        f'<line x1="{random.randint(0, width)}" y1="{random.randint(0, height)}" '
        f'x2="{random.randint(0, width)}" y2="{random.randint(0, height)}" '
        f'stroke="rgba(148,163,184,0.35)" stroke-width="1"/>'
        for _ in range(6)
    )
    chars = []
    x = 16
    for ch in code:
        y = random.randint(28, 36)
        rot = random.randint(-18, 18)
        fill = random.choice(["#38bdf8", "#22d3ee", "#a78bfa", "#34d399"])
        chars.append(
            f'<text x="{x}" y="{y}" fill="{fill}" font-size="22" font-family="monospace" '
            f'font-weight="700" transform="rotate({rot} {x} {y})">{ch}</text>'
        )
        x += 24
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="#0f172a"/>'
        f"{noise}{''.join(chars)}</svg>"
    )


def create_captcha() -> dict:
    _purge_expired()
    captcha_id = secrets.token_urlsafe(16)
    code = _generate_code()
    _CAPTCHA_STORE[captcha_id] = {
        "code": code.upper(),
        "expires_at": time.time() + _CAPTCHA_TTL,
    }
    svg = _svg_for_code(code)
    return {"captcha_id": captcha_id, "svg": svg}


def verify_captcha(captcha_id: str, captcha_code: str) -> bool:
    _purge_expired()
    if not captcha_id or not captcha_code:
        return False
    entry = _CAPTCHA_STORE.pop(captcha_id, None)
    if not entry:
        return False
    if entry["expires_at"] < time.time():
        return False
    return entry["code"] == captcha_code.strip().upper()


@router.get("/api/auth/captcha", summary="Get login captcha")
async def get_captcha():
    data = create_captcha()
    return {"code": 0, "data": data}
