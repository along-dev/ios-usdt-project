"""
Real-time Notification Module.
Supports webhook push to WeChat Work, DingTalk, Telegram, or generic HTTP POST.
"""

from __future__ import annotations

import asyncio
import time
import logging

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from .audit import audit
from .crypto_utils import mask_url
from .database import get_webhook_config, save_webhook_config

router = APIRouter(tags=["Notifications"])
log = logging.getLogger("notifications")


class WebhookConfigRequest(BaseModel):
    webhook_url: str
    webhook_type: str = "generic"
    enabled: bool = True


@router.get("/api/notifications/config", summary="Get webhook config")
async def get_config():
    cfg = get_webhook_config()
    url = cfg.get("webhook_url", "")
    return {
        "code": 0,
        "data": {
            "webhook_url": url,
            "webhook_url_masked": mask_url(url),
            "webhook_type": cfg.get("webhook_type", "generic"),
            "enabled": bool(cfg.get("enabled", 0)),
        },
    }


@router.post("/api/notifications/config", summary="Save webhook config")
async def set_config(req: WebhookConfigRequest):
    save_webhook_config(req.webhook_url, req.webhook_type, req.enabled)
    audit("update_webhook", "notifications:webhook", detail=mask_url(req.webhook_url))
    return {"code": 0, "msg": "Webhook config saved"}


@router.post("/api/notifications/test", summary="Send test notification")
async def test_notification():
    cfg = get_webhook_config()
    if not cfg.get("webhook_url"):
        return {"code": 1, "msg": "No webhook URL configured"}

    test_data = {
        "title": "iOS Security Console - Test",
        "content": f"Webhook test at {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "source": "ios-security-console",
    }

    success = await _send_webhook(cfg["webhook_url"], cfg.get("webhook_type", "generic"), test_data)
    return {"code": 0 if success else 1, "msg": "sent" if success else "failed"}


async def notify_new_visitor(visitor_data: dict):
    """Call this when a new visitor is detected. Non-blocking."""
    cfg = get_webhook_config()
    if not cfg.get("enabled") or not cfg.get("webhook_url"):
        return

    alert = {
        "title": "New Visitor Detected",
        "content": (
            f"IP: {visitor_data.get('ip', '—')}\n"
            f"Device: {visitor_data.get('device_model', '—')}\n"
            f"iOS: {visitor_data.get('ios_version', '—')}\n"
            f"UA: {visitor_data.get('user_agent', '—')[:60]}\n"
            f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        "source": "ios-security-console",
    }

    asyncio.create_task(_send_webhook(cfg["webhook_url"], cfg.get("webhook_type", "generic"), alert))


async def _send_webhook(url: str, wtype: str, data: dict) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if wtype == "wechat_work":
                payload = {
                    "msgtype": "text",
                    "text": {"content": f"{data['title']}\n\n{data['content']}"},
                }
            elif wtype == "dingtalk":
                payload = {
                    "msgtype": "text",
                    "text": {"content": f"{data['title']}\n\n{data['content']}"},
                }
            elif wtype == "telegram":
                payload = {
                    "text": f"*{data['title']}*\n\n```\n{data['content']}\n```",
                    "parse_mode": "Markdown",
                }
            elif wtype == "feishu":
                payload = {
                    "msg_type": "text",
                    "content": {"text": f"{data['title']}\n\n{data['content']}"},
                }
            else:
                payload = data

            resp = await client.post(url, json=payload)
            log.info(f"Webhook sent to {url}: {resp.status_code}")
            return 200 <= resp.status_code < 300
    except Exception as e:
        log.warning(f"Webhook failed: {e}")
        return False
