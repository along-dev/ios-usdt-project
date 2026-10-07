"""
Symmetric encryption helpers for secrets at rest (webhook URLs).
"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _fernet() -> Optional[Fernet]:
    key = os.environ.get("WEBHOOK_ENC_KEY", "").strip()
    if not key:
        seed = os.environ.get("JWT_SECRET", "ios-console-default-key")
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
    elif len(key) != 44:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return value


def mask_url(url: str) -> str:
    if not url:
        return ""
    if "://" not in url:
        return url[:4] + "***" if len(url) > 4 else "***"
    scheme, rest = url.split("://", 1)
    if "@" in rest:
        creds, host = rest.split("@", 1)
        return f"{scheme}://***@{host}"
    if len(rest) <= 12:
        return f"{scheme}://***"
    return f"{scheme}://{rest[:6]}***{rest[-4:]}"
