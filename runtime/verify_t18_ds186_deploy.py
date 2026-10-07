#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T18 [R2] —— darksword 18.6 的部署缺口判据脚本

断言 V1–V6（见 09-docs/cards/T18-darksword18.6部署缺口.md）：
  V1  templates/darksword/rce_worker_18.6.js 存在且 sha256 == 05-ios 源
  V2  templates/darksword/rce_module_18.6.js 存在且 sha256 == 05-ios 源
  V3  ★★★ 「模块注册表无悬空 src」—— DARKSWORD_MODULES + DARKSWORD_MODULES_EXTRA
      的每个 src 都在 templates/darksword/ 存在
  V4  未改 05-ios/darksword/ 的源文件（sha256 未变）
  V5  /api/apk/download 与 /api/template 未回归
  V6  守护：_manifest.sha256、contracts.md 未改

用法：
  python verify_t18_ds186_deploy.py            # 全量（含 V5 网络探测）
  python verify_t18_ds186_deploy.py --no-net   # 跳过 V5

退出码：0 = 全绿；1 = 有断言失败。
P-36：所有文件读取一律 open(p,'rb')，绝不用 text 模式取 bytes。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import hashlib
import json
import os
import re
import sys
import urllib.request

ROOT = USDT_ROOT
TPL_DIR = os.path.join(ROOT, "02-backend-node", "templates", "darksword")
IOS_DIR = os.path.join(ROOT, "05-ios", "darksword")
CHAIN_JS = os.path.join(
    ROOT, "02-backend-node", "src_restored", "plugins", "c2", "services", "chain-darksword.js"
)
SERVER_PY = os.path.join(IOS_DIR, "server.py")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")
CONTRACTS = os.path.join(ROOT, "09-docs", "spec", "contracts.md")

# ── 冻结值（卡面给定） ────────────────────────────────────────────────
SRC_186 = {
    "rce_worker_18.6.js": "f2798a29540c85e73f5c6e98cfd25438c54601eba1ff23a2271cfe9ea9087e02",
    "rce_module_18.6.js": "37efaa4237a28a4be411d40de80b2935be5b8c4e6731ee1f858c609142a87445",
}
SRC_186_BYTES = {"rce_worker_18.6.js": 526012, "rce_module_18.6.js": 85}

# V4：05-ios 源文件改前 sha256 基线（本次实测）
IOS_BASELINE = {
    "rce_worker_18.6.js": "f2798a29540c85e73f5c6e98cfd25438c54601eba1ff23a2271cfe9ea9087e02",
    "rce_module_18.6.js": "37efaa4237a28a4be411d40de80b2935be5b8c4e6731ee1f858c609142a87445",
    "rce_loader.js": "f6d78594778473dec1ae4d75fd71ef7b1a2cccc4cae13ec2d361bdbb8e90d969",
    "rce_worker_18.4.js": "a332fea03341b00493f1ec81f084fa2fee7e470d27e804d5988f89fdb21270c1",
    "sbx0_main_18.4.js": "5d50e79c857025a25913f00ffed013f5cda8f8b2c67082cba320d29f503f6642",
    "sbx1_main.js": "c641cdd53395d2a9ae95bd1588b068921b05aacf87d63c915581049f9923ca2e",
    "pe_main.js": "c5a0e576ffdb6753236168532ef38e45bf6e800ac647392131312aa8b4d6a0aa",
}

# V6：守护文件改前 sha256 基线
GUARD_BASELINE = {
    MANIFEST: "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
    CONTRACTS: "f80a2ead6736d5f5aff70e72e3aa7de1c7cc63f93a604fb6eeb4a163059f925c",
}

results = []


def sha256_of(p):
    """P-36：二进制读取算 sha256。"""
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def check(tag, ok, detail):
    results.append((tag, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print("  [%s] %s: %s" % (mark, tag, detail))
    return ok


# ─────────────────────────────────────────────────────────────────────
def v1_v2():
    print("\n=== V1/V2 · 18.6 两文件已部署且 sha256 == 源 ===")
    for name in ("rce_worker_18.6.js", "rce_module_18.6.js"):
        tpl = os.path.join(TPL_DIR, name)
        src = os.path.join(IOS_DIR, name)
        if not os.path.exists(tpl):
            check(name, False, "templates/darksword/%s 不存在" % name)
            continue
        h_tpl = sha256_of(tpl)
        h_src = sha256_of(src)
        size = os.path.getsize(tpl)
        ok = (h_tpl == h_src) and (h_tpl == SRC_186[name]) and (size == SRC_186_BYTES[name])
        check(
            name,
            ok,
            "sha(模板)=%s sha(源)=%s bytes=%d(期望%d) %s"
            % (h_tpl[:16] + "…", h_src[:16] + "…", size, SRC_186_BYTES[name],
               "OK" if ok else "不一致"),
        )


def parse_registry():
    """从 chain-darksword.js 抽取 DARKSWORD_MODULES / DARKSWORD_MODULES_EXTRA 的 src。"""
    with open(CHAIN_JS, "rb") as f:
        text = f.read().decode("utf-8")

    def grab(export_name):
        m = re.search(
            r"export\s+const\s+%s\s*=\s*\[(.*?)\n\s*\];" % re.escape(export_name),
            text,
            re.S,
        )
        if not m:
            return None
        body = m.group(1)
        return re.findall(r"src:\s*'([^']+)'", body)

    base = grab("DARKSWORD_MODULES")
    extra = grab("DARKSWORD_MODULES_EXTRA")
    return base, extra


def v3():
    print("\n=== V3 · ★★★ 模块注册表无悬空 src ===")
    base, extra = parse_registry()
    if base is None or extra is None:
        check("V3-parse", False, "无法从 chain-darksword.js 解析出注册表数组")
        return
    check(
        "V3-parse",
        True,
        "DARKSWORD_MODULES=%d 项, DARKSWORD_MODULES_EXTRA=%d 项（抽取非空）"
        % (len(base), len(extra)),
    )
    if not base or not extra:
        check("V3-nonempty", False, "抽取结果为空，量尺不可信")
        return

    dangling = []
    print("  ── 逐 src 存在性 ──")
    for label, names in (("MODULES", base), ("EXTRA", extra)):
        for s in names:
            tpl = os.path.join(TPL_DIR, s)
            exists = os.path.exists(tpl)
            print("    [%s] %-9s %-24s" % ("OK  " if exists else "MISS", label, s))
            if not exists:
                dangling.append(s)
    check(
        "V3-no-dangling",
        len(dangling) == 0,
        "悬空 src 数 = %d %s"
        % (len(dangling), ("(" + ", ".join(dangling) + ")") if dangling else "(全部命中)"),
    )


def v4():
    print("\n=== V4 · 未改 05-ios/darksword/ 源文件 ===")
    bad = []
    for name, expect in IOS_BASELINE.items():
        p = os.path.join(IOS_DIR, name)
        if not os.path.exists(p):
            bad.append("%s(缺失)" % name)
            continue
        h = sha256_of(p)
        if h != expect:
            bad.append("%s(%s→%s)" % (name, expect[:12], h[:12]))
    check(
        "V4-sources-unchanged",
        len(bad) == 0,
        "7 个源文件 sha256 全部未变" if not bad else "被改动: " + "; ".join(bad),
    )


def v5(skip_net):
    print("\n=== V5 · /api/apk/download 与 /api/template 未回归 ===")
    if skip_net:
        print("  [SKIP] --no-net")
        return
    targets = [
        ("http://127.0.0.1:3000/api/apk/download", 200, None),
        ("http://127.0.0.1:3000/api/template", 200, None),
    ]
    for url, want, _ in targets:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                code = r.getcode()
            ok = code == want and len(body) > 0
            note = ""
            if url.endswith("/api/template"):
                try:
                    j = json.loads(body.decode("utf-8"))
                    ok = ok and "template" in j
                    note = " body=%s" % json.dumps(j, ensure_ascii=False)
                except Exception as e:
                    ok = False
                    note = " JSON 解析失败: %s" % e
            check(url.rsplit("/api/", 1)[1], ok, "HTTP %d len=%d%s" % (code, len(body), note))
        except Exception as e:
            check(url.rsplit("/api/", 1)[1], False, "请求失败: %s" % e)


def v6():
    print("\n=== V6 · 守护文件未改 ===")
    for path, expect in GUARD_BASELINE.items():
        if not os.path.exists(path):
            check(os.path.basename(path), False, "文件缺失")
            continue
        h = sha256_of(path)
        check(
            os.path.basename(path),
            h == expect,
            "sha256=%s %s" % (h[:16] + "…", "未变" if h == expect else "★ 已变"),
        )


def main():
    skip_net = "--no-net" in sys.argv
    print("=" * 68)
    print("T18 —— darksword 18.6 部署缺口判据（V1–V6）")
    print("=" * 68)

    v1_v2()
    v3()
    v4()
    v5(skip_net)
    v6()

    failed = [t for t, ok, _ in results if not ok]
    print("\n" + "=" * 68)
    print("汇总：%d 项断言，%d 通过，%d 失败" % (len(results), len(results) - len(failed), len(failed)))
    if failed:
        for t in failed:
            print("   FAIL: %s" % t)
        print("RESULT=RED")
        return 1
    print("RESULT=GREEN  T18 全部判据通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
