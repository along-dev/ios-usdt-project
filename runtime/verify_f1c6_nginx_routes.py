# -*- coding: utf-8 -*-
"""
F1-C6 判据：nginx 路由归属 —— 管理台(Go:8888) 与 落地页(Node:3000) 各归其位。

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

用法：
    python verify_f1c6_nginx_routes.py            # 对产物
    python verify_f1c6_nginx_routes.py --selftest # 量尺前置断言（P-5）

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 旧版 Python 无 reconfigure 时静默降级
import argparse
import hashlib
import os
import re
import sys

ROOT = USDT_ROOT
NGINX = os.path.join(ROOT, "08-infra", "nginx", "default.conf.template")
COMPOSE = os.path.join(ROOT, "08-infra", "compose", "docker-compose.yml")

# 调度表固定的端口（不得改）
PORTS = {"go": "8888", "node": "3000"}


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _extract_block(src, open_idx):
    """
    从 open_idx 的 '{' 开始，按大括号配对取出完整块体（含花括号）。
    ★ 不能用 [^}]* —— 块内出现 ${VAR} 时会在第一个 '}' 处提前终止
      （实测导致 go_server 的 server 行被截断为 'server ${ADMIN_BACKEND_HOST'）。
    """
    depth = 0
    i = open_idx
    while i < len(src):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[open_idx:i + 1]
        i += 1
    return src[open_idx:]


def parse_upstreams(src):
    """
    解析 upstream 块 -> {name: 'host:port'}
    ★ 支持 nginx 环境变量占位形态 server ${VAR}:8888（实测本配置用到）。
    """
    out = {}
    for m in re.finditer(r"upstream\s+(\w+)\s*\{", src):
        name = m.group(1)
        block = _extract_block(src, m.end() - 1)
        s = re.search(r"server\s+([\w.${}\\-]+):(\d+)", block)
        if s:
            out[name] = f"{s.group(1)}:{s.group(2)}"
    return out


def _strip_var(host):
    """把 ${VAR} 形态归一为占位名，便于端口判定与服务对应判定。"""
    return re.sub(r"\$\{[^}]+\}", "VAR", host)


def parse_servers(src):
    """
    解析每个 server 块的 (server_name, locations)。
    ★ 全程用大括号配对取块，不用 [^}]*（需支持块内 ${VAR}）。
    """
    servers = []
    for m in re.finditer(r"server\s*\{", src):
        block = _extract_block(src, m.end() - 1)
        sn = re.search(r"server_name\s+([^;]+);", block)
        server_name = sn.group(1).strip() if sn else ""
        locs = []
        for lm in re.finditer(r"location\s+([^\s{]+)\s*\{", block):
            lblock = _extract_block(block, lm.end() - 1)
            prefix = lm.group(1)
            pp = re.search(r"proxy_pass\s+([^;]+);", lblock)
            target = pp.group(1).strip() if pp else None
            has_rewrite = "rewrite" in lblock
            locs.append((prefix, target, has_rewrite))
        servers.append({"name": server_name, "locations": locs, "raw": block})
    return servers


def find_server_for(servers, domain):
    """找匹配某域名的 server 块"""
    for s in servers:
        names = s["name"].split()
        for n in names:
            if n == domain:
                return s
            if n.startswith("*.") and domain.endswith(n[1:]):
                return s
    return None


def selftest():
    """量尺前置断言（P-5）：用合成 nginx 配置证明解析器有效"""
    print("=== 量尺前置断言（P-5）===")
    ok = True
    fake = """
    upstream app_server { server server:3000; }
    upstream go_server { server ${ADMIN_BACKEND_HOST}:8888; }
    server {
        listen 80;
        server_name admin.example.com;
        location /api/ { proxy_pass http://go_server; rewrite ^/api/(.*)$ /$1 break; }
    }
    """
    ups = parse_upstreams(fake)
    if ups.get("app_server") != "server:3000":
        print(f"  [FAIL] upstream 解析失败: {ups}")
        ok = False
    else:
        print(f"  upstream 解析有效: {ups}")

    # ★ 专项回归断言：${VAR} 形态的 upstream 必须能解析出来
    #   （历史缺陷：块体正则用 [^}]*，在 ${VAR} 的 '}' 处提前终止）
    if ups.get("go_server") != "${ADMIN_BACKEND_HOST}:8888":
        print(f"  [FAIL] ${VAR} 形态 upstream 解析失败: {ups}")
        ok = False
    else:
        print("  ${VAR} 形态 upstream 解析有效")

    srvs = parse_servers(fake)
    if not srvs:
        print("  [FAIL] server 块解析失败")
        ok = False
    else:
        s = find_server_for(srvs, "admin.example.com")
        if not s:
            print("  [FAIL] server_name 匹配失败")
            ok = False
        else:
            locs = s["locations"]
            if not locs or locs[0][1] != "http://go_server" or not locs[0][2]:
                print(f"  [FAIL] location/rewrite 解析失败: {locs}")
                ok = False
            else:
                print(f"  location+rewrite 解析有效: {locs[0]}")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--admin-domain", default=os.environ.get("ADMIN_DOMAIN", ""))
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not os.path.isfile(NGINX):
        print(f"[FAIL] nginx 配置不存在: {NGINX}")
        return 1

    src = read(NGINX)
    ups = parse_upstreams(src)
    servers = parse_servers(src)
    # ★ T110（G-10）：计数判据同句打印被测文件快照哈希，把「期望值」与「磁盘真值」分离。
    snap = hashlib.sha256(src.encode("utf-8")).hexdigest()

    print(f"nginx 配置: {NGINX}")
    print(f"upstreams: {ups}")
    print(f"server 块数: {len(servers)}  snapshot_sha256={snap}")
    for s in servers:
        print(f"  server_name='{s['name']}' locations={[(l[0], l[1], l[2]) for l in s['locations']]}")
    print("")

    fails = []

    # R1: 管理台前缀不得落到 Node upstream
    #     判据：必须存在一个 upstream 指向 Go:8888，且管理台 server 块中
    #     /base/ 或 /user/ 的 proxy_pass 指向它（不是 app_server）
    go_up = [n for n, t in ups.items() if t.endswith(":" + PORTS["go"])]
    node_up = [n for n, t in ups.items() if t.endswith(":" + PORTS["node"])]
    print(f"指向 Go:{PORTS['go']} 的 upstream: {go_up}")
    print(f"指向 Node:{PORTS['node']} 的 upstream: {node_up}")

    if not go_up:
        print(f"  [FAIL] R1 无任何 upstream 指向 Go:{PORTS['go']} —— 管理台无路由目标")
        fails.append("R1-no-go-upstream")
    else:
        # 找管理台 server：含 /base/ 或 /user/ location
        admin_srv = None
        for s in servers:
            prefs = [l[0] for l in s["locations"]]
            if any(p.startswith("/base") for p in prefs) or any(p.startswith("/user") for p in prefs):
                admin_srv = s
                break
        if not admin_srv:
            print("  [FAIL] R1 未找到含 /base/ 或 /user/ 的管理台 server 块")
            fails.append("R1-no-admin-server")
        else:
            print(f"  管理台 server_name='{admin_srv['name']}'")
            for prefix, target, rw in admin_srv["locations"]:
                if prefix.startswith(("/base", "/user")):
                    ok = target is not None and any(g in (target or "") for g in go_up)
                    mark = "PASS" if ok else "FAIL"
                    print(f"  [{mark}] R1 location {prefix} -> {target} (rewrite={rw})")
                    if not ok:
                        fails.append(f"R1-{prefix}-not-go")

    # R2: 落地页 /api/ 仍必须落到 Node（防改过头）
    node_api_ok = False
    for s in servers:
        for prefix, target, rw in s["locations"]:
            if prefix == "/api/" and target and any(n in target for n in node_up):
                node_api_ok = True
    if node_api_ok:
        print("  [PASS] R2 落地页 /api/ 仍指向 Node upstream（防改过头）")
    else:
        print("  [FAIL] R2 落地页 /api/ 未指向 Node —— 可能改坏了落地页")
        fails.append("R2-api-not-node")
    print("")

    # R3: 每个 upstream 名在 compose 中有对应服务或已声明外部提供
    print("R3 upstream 与服务对应核对:")
    comp = read(COMPOSE)
    comp_services = set(re.findall(r"^\s{2}(\w+):", comp, re.M))
    print(f"  compose 服务: {sorted(comp_services)}")
    for name, target in ups.items():
        host = target.split(":")[0]
        host_n = _strip_var(host)
        if host in comp_services:
            print(f"  [PASS] R3 upstream {name} -> {host} 在 compose 中存在")
        elif host_n == "VAR":
            # ★ 处置 (b2)：Go 由 compose 外提供，主机名来自环境变量。
            #   合规性要求：该变量必须在 compose 的 nginx.environment 中注入。
            env_declared = "ADMIN_BACKEND_HOST" in comp and "environment" in comp
            if env_declared:
                print(f"  [PASS] R3 upstream {name} -> {host} 由 compose 注入变量提供（处置 b2：compose 外提供）")
            else:
                print(f"  [FAIL] R3 upstream {name} -> {host} 使用变量但 compose 未注入")
                fails.append(f"R3-undeclared-var:{name}")
        else:
            print(f"  [FAIL] R3 upstream {name} -> {host} 在 compose 中无对应服务且未声明外部提供")
            fails.append(f"R3-no-service:{host}")
    print("")

    # R4: 端口与调度表一致
    print("R4 端口一致性核对:")
    for name, target in ups.items():
        port = target.split(":")[-1]
        if port in PORTS.values():
            print(f"  [PASS] R4 {name} 端口 {port} 符合调度表")
        else:
            print(f"  [FAIL] R4 {name} 端口 {port} 不在调度表 {PORTS}")
            fails.append(f"R4-bad-port:{port}")
    print("")

    if fails:
        print(f"RESULT=RED  失败项: {fails}")
        return 1
    print("RESULT=GREEN  管理台归 Go、落地页归 Node、upstream 有服务")
    return 0


if __name__ == "__main__":
    sys.exit(main())
