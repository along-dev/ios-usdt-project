# -*- coding: utf-8 -*-
"""T28（WBE01-B）**反向断言**：`casbin_rbac.go` 的 `develop` 旁路**已删除**。

R-A（★ 本卡核心）：`Env=develop` ＋ **未授权** authority（`1234`）⇒ 受保护端点 ⇒ **`code:7`**
R-B（正控）      ：**已授权** authority（`888`）⇒ 同端点 ⇒ **`code:0`**
R-C（负控）      ：`Env=production` ＋ 未授权 ⇒ 同端点 ⇒ **`code:7`**

★ 守契约 **C-2**：**只看 body 的 `code`，⛔ 不看 HTTP 状态**。
★ 会话用 `rbac_login.py` 的**自签 JWT**（不改该件，只在内存里把它的 `GO` 指到目标）。
★ 目标实例由 `DSH_API` 指定（默认 `http://127.0.0.1:8888`；本卡用 **8899**）。
★ `REGIME`（`develop`/`production`）仅用于**标注读数**与判读，不改行为。

用法：
    DSH_API=http://127.0.0.1:8899 REGIME=develop    python t28_casbin_assert.py
    DSH_API=http://127.0.0.1:8899 REGIME=production python t28_casbin_assert.py
退出码：0 = 与 REGIME 的期望相符；1 = 有红。
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

_os = os
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API = os.environ.get("DSH_API", "http://127.0.0.1:8888")
assert API in ("http://127.0.0.1:8900", "http://127.0.0.1:8899"), "⛔ 拒绝裸跑：只允许隔离实例 8900/8899（8888 是共享实例）"
REGIME = os.environ.get("REGIME", "develop").strip().lower()
_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("rbac", os.path.join(_here, "rbac_login.py"))
rbac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rbac)
rbac.GO = API                      # ★ 只改内存里的基址，⛔ 不动 rbac_login.py 这个文件

UNAUTH = rbac.mint(101, "agentA", "代理商A", "1234", "11111111-1111-1111-1111-111111111111")
ADMIN = rbac.mint(8, "admin", "超级管理员", "888", "b059de9e-be0c-11f1-9ed6-14755b847ee7")
PATH_ = "/device/list"
BODY = {"page": 1, "pageSize": 10, "status": -1, "agent_id": -1}


def code_of(resp):
    s, b = resp
    if isinstance(b, dict):
        return s, b.get("code"), (b.get("msg") or "")[:60]
    return s, None, str(b)[:60]


def main():
    print(f"=== T28 反向断言 · 目标 {API} · REGIME={REGIME} ===")
    rows = []
    s, c, m = code_of(rbac.call(PATH_, UNAUTH, BODY))
    rows.append(("R-A", "未授权(1234)", s, c, m))
    s2, c2, m2 = code_of(rbac.call(PATH_, ADMIN, BODY))
    rows.append(("R-B", "已授权(888)", s2, c2, m2))
    for rid, who, st, c, m in rows:
        print(f"  {rid} {who:14s} HTTP={st} code={c} msg={m}")
    print(f"  R-C 与 R-A 同形；本实例的 REGIME={REGIME} ⇒ "
          + ("R-A 即 develop 下的核心断言" if REGIME == "develop" else "R-C 即 production 下未授权"))

    ok = True
    if REGIME == "develop":
        # ★ 核心：develop 下**未授权也必须被拒**（旁路已删）
        ok &= (rows[0][3] is not None and rows[0][3] != 0)
        ok &= (rows[1][3] == 0)
        print("  判读（develop）：R-A 必须 code≠0（旁路已删）＋ R-B 必须 code==0")
    else:
        ok &= (rows[0][3] is not None and rows[0][3] != 0)
        ok &= (rows[1][3] == 0)
        print("  判读（production）：R-C 必须 code≠0 ＋ R-B 必须 code==0")
    print("T28_ASSERT=" + ("OK" if ok else "BAD"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
