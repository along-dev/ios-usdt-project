# -*- coding: utf-8 -*-
"""R3-1 后续：逐个诊断主回归集的 9 个失败，区分【真缺陷】与【环境/预期变更】。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import os
import subprocess
import sys

ROOT = IOS_ROOT + r"\_integration\_fix_work"
PY = sys.executable
NODE = r"E:\CTF\runtime\node\node.exe"

FAILS = [
    "verify_d2c2_templates_consistency.py",
    "verify_d2c5_filzaslop_static.py",
    "verify_doc_freshness.py",
    "verify_f1c10_bridge_e2e.mjs",
    "verify_t19_dashboards.py",
    "verify_t21_previews.py",
    "verify_t22_bill_endpoint.py",
]

env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
env["PATH"] = r"E:\CTF\runtime\node;" + env.get("PATH", "")

for f in FAILS:
    p = os.path.join(ROOT, f)
    if not os.path.isfile(p):
        print("=== %s ===" % f)
        print("  [缺失]")
        continue
    cmd = [NODE, p] if f.endswith(".mjs") else [PY, p]
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=90, env=env)
        out = r.stdout.decode("utf-8", "replace")
        err = r.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        print("=== %s ===" % f)
        print("  TIMEOUT >90s")
        continue
    print("=== %s (rc=%d) ===" % (f, r.returncode))
    # 只看最后 12 行（判据通常末尾打印结论）
    lines = [l for l in out.splitlines() if l.strip()]
    for l in lines[-12:]:
        print("   ", l[:150])
    if err.strip():
        for l in err.strip().splitlines()[-4:]:
            print("  [err]", l[:150])
    print("")
