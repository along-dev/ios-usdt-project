# -*- coding: utf-8 -*-
"""T26 / ①A-6 · 服务绑定合规断言（可复现）。

★ 依据：
  · 审核 C 的 C-4：8888/3000/8080 曾绑全网卡；DB 三件套正确绑 loopback。
  · 上线加固清单 §一-2：**DB 三件套必须保持 loopback**。

★ 本脚本断言【DB 三件套】的监听地址必须是 127.0.0.1（或 ::1）。
★ 对 8888/3000/8080：**只报告不判红**（它们是待加固项，见清单 §二-3），
  但在输出中【显式提示】当前绑定状态（便于部署时对照）。

★ 退出码：DB 三件套合规 ⇒ 0；否则 ⇒ 1。
"""
import re
import subprocess
import sys

# DB 三件套：必须 loopback
DB_PORTS = {13306: "MariaDB", 16379: "Redis", 27018: "MongoDB"}
# 应用端口：当前允许全网卡（部署期加固项），只报告
APP_PORTS = {8888: "Go", 3000: "Node", 8080: "Proxy(测试设施)"}
LOOPBACK = ("127.0.0.1", "::1")


def listeners():
    """用 netstat 取监听地址（-a -n -p tcp）。"""
    try:
        r = subprocess.run(["netstat", "-a", "-n"],
                           capture_output=True, timeout=30)
        out = r.stdout.decode("utf-8", "replace")
    except Exception as e:
        print("  [FAIL] 无法执行 netstat: %s" % e)
        return {}
    res = {}
    for line in out.splitlines():
        # 形如：  TCP    0.0.0.0:8888           0.0.0.0:0              LISTENING
        m = re.search(r"^\s*TCP\s+(\S+):(\d+)\s+\S+\s+LISTENING", line)
        if not m:
            continue
        addr, port = m.group(1), int(m.group(2))
        res.setdefault(port, []).append(addr)
    return res


def main():
    print("=== T26/1A-6 服务绑定合规断言 ===")
    print("")
    ls = listeners()
    if not ls:
        print("  [FAIL] netstat 无输出 ⇒ 无法判定")
        return 1

    fails = []
    print("--- ① DB 三件套（★ 必须 loopback，判红）---")
    for port, name in sorted(DB_PORTS.items()):
        addrs = ls.get(port, [])
        if not addrs:
            print("  [FAIL] %-8s :%-6d 未监听" % (name, port))
            fails.append("%s:%d 未监听" % (name, port))
            continue
        bad = [a for a in addrs if a not in LOOPBACK]
        if bad:
            print("  [FAIL] %-8s :%-6d ★ 非 loopback: %s" % (name, port, bad))
            fails.append("%s:%d 绑定 %s" % (name, port, bad))
        else:
            print("  [PASS] %-8s :%-6d 仅 loopback %s" % (name, port, addrs))

    print("")
    print("--- ② 应用端口（加固清单 §二-3 的待办项，★ 只报告不判红）---")
    for port, name in sorted(APP_PORTS.items()):
        addrs = ls.get(port, [])
        if not addrs:
            print("  [INFO] %-16s :%-6d 未监听" % (name, port))
            continue
        wide = [a for a in addrs if a not in LOOPBACK]
        mark = "★ 全网卡（上线前须改）" if wide else "仅 loopback（已加固）"
        print("  [INFO] %-16s :%-6d %s  %s" % (name, port, addrs, mark))

    print("")
    print("=" * 60)
    if fails:
        print("RESULT=RED  DB 三件套绑定不合规:")
        for f in fails:
            print("   - " + f)
        return 1
    print("RESULT=GREEN  DB 三件套均仅绑 loopback")
    return 0


if __name__ == "__main__":
    sys.exit(main())
