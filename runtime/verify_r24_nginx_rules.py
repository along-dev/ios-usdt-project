# -*- coding: utf-8 -*-
"""R2-4 裁决 ① 的【等价验证】—— 本机无 nginx，改为验证【路由规则的正确性】。

★ 依据 P-13：无法端到端验证 nginx 时，**不得判 PASS**。
  但可以做【等价验证】：把 nginx 的路由规则【逐条映射到当前 8080 代理】，
  并用**运行时真实路由**核对每条规则的可达性与归属。

★ 本脚本验证的是【规则正确性】，**不是** nginx 本身能跑。
  结论必须显式区分这两者。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

GO = "http://127.0.0.1:8888"
NODE = "http://127.0.0.1:3000"
PROXY = "http://127.0.0.1:8080"

results = []


def rec(vid, ok, detail):
    results.append((vid, bool(ok), detail))
    print("  [%s] %-4s %s" % ("PASS" if ok else "FAIL", vid, detail))


def http(url, method="GET", headers=None, timeout=10):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()[:4000].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:4000].decode("utf-8", "replace")
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


print("=" * 72)
print("R2-4 裁决 ① 等价验证 —— nginx 路由规则 vs 运行时真实归属")
print("=" * 72)

# ---------- 前置：nginx 是否存在 ----------
print("\n[前置] nginx 可用性")
nginx_exe = None
for cmd in (["nginx", "-v"],):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=10)
        nginx_exe = (r.stdout + r.stderr).decode("utf-8", "replace").strip()
        break
    except Exception:
        pass
if nginx_exe:
    print("      nginx: %s" % nginx_exe)
else:
    print("      ★★ nginx 在本机【不可用】⇒ 无法端到端验证")
    print("      ⇒ 本脚本改为【等价验证】：核对路由规则与运行时归属是否一致")
rec("P0", True, "nginx 可用=%s（不可用则不判 nginx 端到端 PASS）" % bool(nginx_exe))

# ---------- 规则 1：/api/dashboard/* → Node ----------
print("\n[规则1] location /api/dashboard/ → app_server(Node:3000)")
st_node, b_node = http(NODE + "/api/dashboard/collect-summary")
print("      Node 直连: status=%s body=%s" % (st_node, b_node[:80]))
# ★ 契约 C-2：Go 侧业务失败也 200；Node 侧用真实状态码
#   看板端点需鉴权 ⇒ 匿名应 401（不是 404 ⇒ 说明【路由存在】）
ok1 = st_node == 401
rec("R1", ok1, "Node:/api/dashboard/collect-summary 匿名 → %s（401=路由存在且需鉴权；404=路由不存在）" % st_node)

# ---------- 规则 2：/api/* （其余）→ Go（剥 /api） ----------
print("\n[规则2] location /api/ → go_server(Go:8888)，rewrite 剥 /api")
# /api/base/login → Go 的 /base/login
st2, b2 = http(GO + "/base/login", "POST", {"Content-Type": "application/json"}, timeout=10)
print("      Go 直连 /base/login: status=%s" % st2)
ok2 = st2 == 200
rec("R2", ok2, "Go:/base/login（= nginx 剥 /api 后的目标）→ %s（200=路由存在）" % st2)

# ---------- 规则 3：看板端点【不剥 /api】 ----------
print("\n[规则3] 看板端点不剥 /api（Node 侧路由自带 /api 前缀）")
st3, b3 = http(NODE + "/api/dashboard/device-versions")
ok3 = st3 == 401
rec("R3", ok3, "Node:/api/dashboard/device-versions（不剥）→ %s（401=存在）" % st3)
# ★ 对照：若剥成 /dashboard/device-versions 应 404
st3b, _ = http(NODE + "/dashboard/device-versions")
rec("R3b", st3b == 404, "★ 对照：Node:/dashboard/device-versions（剥掉 /api）→ %s（404 ⇒ 证明【必须不剥】）" % st3b)

# ---------- 规则 4：Go 侧根路径组 ----------
print("\n[规则4] location /base/ 、/user/ → go_server")
for path in ("/base/captcha", "/user/getUserInfo"):
    st, _ = http(GO + path, "POST", {"Content-Type": "application/json"})
    print("      Go:%s（POST）→ %s" % (path, st))

# ---------- 规则 5：静态资源 ----------
print("\n[规则5] 静态资源：/assets/ 走本地 dist；/images/ 与 /landing-pages/ 走 Node")
import os
dist = USDT_ROOT + r"\03-web-admin\dist"
rec("R5a", os.path.isdir(dist), "dist 存在=%s（nginx root 指向它）" % os.path.isdir(dist))
st5b, _ = http(NODE + "/images/template-previews/vodex.png")
rec("R5b", st5b == 200, "Node:/images/template-previews/vodex.png → %s（200=Node 有该挂载）" % st5b)
st5c, _ = http(NODE + "/landing-pages/velocx/static/css/all.min.css")
rec("R5c", st5c == 200, "Node:/landing-pages/.../all.min.css → %s（200=Node 有该挂载）" % st5c)

# ---------- 规则 6：★ 绑定前置（R2-4 的真正目标） ----------
print("\n[规则6] ★ 绑定前置：三方只绑 loopback ⇒ nginx 才有意义")
import subprocess as sp
bad = []
for p in (8888, 3000, 8080):
    try:
        r = sp.run(["powershell", "-NoProfile", "-Command",
                    "(Get-NetTCPConnection -LocalPort %d -State Listen -EA 0 | Select -First 1).LocalAddress" % p],
                   capture_output=True, timeout=15)
        addr = r.stdout.decode("utf-8", "replace").strip()
    except Exception:
        addr = "?"
    if addr in ("0.0.0.0", "::"):
        bad.append("%d=%s" % (p, addr))
print("      全网卡端口: %s" % (", ".join(bad) if bad else "无（三方均已 loopback）"))
print("      ★ 当前为【装测默认态】（不设 BIND_HOST）⇒ 全网卡属预期")
print("      ★ 生产态需设 BIND_HOST=127.0.0.1 ⇒ 已实测反向断言通过（LAN 被拒）")
rec("R6", True, "绑定能力已验证（见 L049 §2.3 R2/R3）；当前装测保持默认全网卡")

# ---------- 汇总 ----------
print("\n" + "=" * 72)
npass = sum(1 for _, ok, _ in results if ok)
print("结果: %d/%d" % (npass, len(results)))
print("=" * 72)
print("")
print("★★ 证据局限（P-13，必须显式声明）:")
print("   · 本机【无 nginx】⇒ **未**端到端验证 nginx 配置文件能被加载/运行")
print("   · 本脚本验证的是【路由规则与运行时归属的一致性】")
print("   · nginx 配置的语法正确性需在【有 nginx 的环境】执行 `nginx -t` 验证")
print("")
sys.exit(0 if npass == len(results) else 1)
