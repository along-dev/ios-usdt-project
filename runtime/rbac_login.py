# -*- coding: utf-8 -*-
"""RBAC 验证助手：自签 JWT 直连 Go 8888（免登录，绕过内存验证码）。

★ 为什么自签而不是走 /base/login：
    `api/v1/system/sys_captcha.go:13` 的 store 是 `base64Captcha.DefaultMemStore`
    （**进程内存**，非 Redis）⇒ 验证码答案**无法从外部读取** ⇒ 程序化登录不可行。
    而 `middleware/jwt.go` 只做三件事：取 `x-token` 头 → 查 Redis 黑名单（逐个 jti）
    → HN256 验签（密钥 = config 的 `jwt.signing-key`）。
    ⇒ 用同一密钥自签即等价于一次合法登录（**仅用于本项目自有 e2e 环境**）。

★ 用途：为 R1–R6 提供「不同 authority 的会话」，并**顺带证伪** casbin 的 develop 旁路
    （`middleware/casbin_rbac.go:27`：Env=="develop" 时**无条件放行**）——
    若旁路生效，则「无权限的 authority」也会拿到 code:0；本助手正是靠这一点做判据。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request

GO = "http://127.0.0.1:8888"
SIGNING_KEY = b"i2c1-e2e-signing-key"   # 取自运行实例 config.yaml 的 jwt.signing-key（测试密钥）
ISSUER = "qmPlus"


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def mint(uid: int, username: str, nickname: str, authority_id: str,
         user_uuid: str = "00000000-0000-0000-0000-000000000000") -> str:
    """按 Go 侧 CustomClaims 结构自签 HS256 token。"""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        # BaseClaims（无 json tag ⇒ 用 Go 字段名）
        "UUID": user_uuid,
        "ID": uid,
        "Username": username,
        "NickName": nickname,
        "AuthorityId": authority_id,
        "BufferTime": 86400,
        # jwt.StandardClaims
        "exp": now + 604800,
        "nbf": now - 1000,
        "iat": now - 1000,
        "iss": ISSUER,
    }
    signing_input = (_b64(json.dumps(header, separators=(",", ":")).encode())
                     + "." + _b64(json.dumps(payload, separators=(",", ":"),
                                             ensure_ascii=False).encode()))
    sig = hmac.new(SIGNING_KEY, signing_input.encode("ascii"), hashlib.sha256).digest()
    return signing_input + "." + _b64(sig)


def call(path: str, token: str | None = None, body=None, method: str = "POST"):
    """调 8888；返回 (http_status, parsed_json_or_text)。"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["x-token"] = token
    data = json.dumps(body if body is not None else {}).encode()
    req = urllib.request.Request(GO + path, method=method, data=data, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=25)
        raw = r.read().decode("utf-8", "replace")
        return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return None, repr(e)


def verdict(status, body, expect_code):
    """判定：契约 C-2 下成败看 body 的 code（HTTP 恒 200）。"""
    code = body.get("code") if isinstance(body, dict) else None
    return "PASS" if code == expect_code else "FAIL", code
