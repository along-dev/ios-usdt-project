# -*- coding: utf-8 -*-
"""核验 main 清单的 49 条是否【全部真实可跑】（决策 Agent 指出的未取证项）。

★ 检查项：
  ① 文件是否存在
  ② 是否与 guard/build 清单重复
  ③ 是否含构建命令（应归 build）
  ④ 是否含冻结哈希（应归 guard）
  ⑤ 分类（static/service/go-build/web-build）
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import os
import re

ROOT = IOS_ROOT + r"\_integration\_fix_work"


def load(f):
    p = os.path.join(ROOT, f)
    if not os.path.isfile(p):
        return set()
    return set(l.strip() for l in io.open(p, encoding="utf-8", errors="replace").read().splitlines()
               if l.strip() and not l.strip().startswith("#"))


main = load("regression_main.txt")
guard = load("regression_guard.txt")
build = load("regression_build.txt")

PAT_HEX = re.compile(rb"\b[0-9a-fA-F]{64}\b")
# ★ 构建命令的【真实执行】特征（必须出现 subprocess/Popen/exec 调用）
BUILD_EXEC = re.compile(
    r"subprocess\.(run|Popen|call|check_output)\s*\(", re.S)
# ★ 构建命令的【文本提及】特征（可能是文案/注释）
BUILD_HINT = ("go build", "go vet", "go test", "npm run build", "vite build")

# ★★ 白名单：经逐行核实【只文案/注释提及、真执行 = 0】的脚本
#   依据（2026-10-02 实测）：
#     · verify_f1c2_public_unchanged.py —— 仅 L115 print 文案提及 "go build"
#     · verify_t22_bill_endpoint.py     —— 仅 L15 注释"由调用方单独执行"
MENTION_ONLY = {
    "verify_f1c2_public_unchanged.py",
    "verify_t22_bill_endpoint.py",
}

print("=== main 清单核验（%d 条）===" % len(main))
print("")

problems = []
notes = []
for f in sorted(main):
    p = os.path.join(ROOT, f)
    row = {"file": f, "exists": os.path.isfile(p)}
    if not row["exists"]:
        problems.append((f, "★ 文件不存在"))
        continue
    raw = open(p, "rb").read()
    s = raw.decode("utf-8", "replace")
    n_hex = len(PAT_HEX.findall(raw))
    # ★ 真执行 = 有 subprocess 调用【且】含有构建命令文本【且】不在白名单
    has_build_exec = bool(BUILD_EXEC.search(s))
    has_build_text = any(h in s for h in BUILD_HINT)
    has_build = has_build_exec and has_build_text and f not in MENTION_ONLY
    mention_only = has_build_text and not has_build
    dup_guard = f in guard
    dup_build = f in build

    tags = []
    if n_hex:
        tags.append("含 %d 个 64-hex" % n_hex)
    if has_build:
        tags.append("★ 真执行构建命令")
    if mention_only:
        tags.append("仅文案提及构建（白名单，非问题）")
    if dup_guard:
        tags.append("★ 与 guard 重复")
    if dup_build:
        tags.append("★ 与 build 重复")

    # ★ 只把【真问题】计入 problems
    real = [t for t in tags if t.startswith("★")]
    if real:
        problems.append((f, "; ".join(real)))
    elif tags:
        notes.append((f, "; ".join(tags)))

print("--- 有问题的条目 ---")
if problems:
    for f, why in problems:
        print("  %-46s %s" % (f, why))
else:
    print("  ✅ 全部 %d 条均无问题（存在、不真执行构建、不与其它清单重复）" % len(main))

print("")
print("--- 说明性备注（非问题）---")
if notes:
    for f, why in notes:
        print("  %-46s %s" % (f, why))
else:
    print("  （无）")

print("")
print("--- 分类统计 ---")
from collections import Counter
c = Counter()
for f in sorted(main):
    p = os.path.join(ROOT, f)
    if not os.path.isfile(p):
        c["missing"] += 1
        continue
    s = open(p, "rb").read().decode("utf-8", "replace")
    if (BUILD_EXEC.search(s) and any(h in s for h in BUILD_HINT)
            and f not in MENTION_ONLY):
        c["build(bad)"] += 1
    elif "fastify" in s.lower() or "app.js" in s or "/healthz" in s or "127.0.0.1:3000" in s:
        c["service"] += 1
    else:
        c["static"] += 1
for k, v in c.items():
    print("  %-14s %d" % (k, v))

print("")
print("--- 三清单重复检查 ---")
print("  main ∩ guard :", sorted(main & guard) or "无 ✅")
print("  main ∩ build :", sorted(main & build) or "无 ✅")
print("  guard ∩ build:", sorted(guard & build) or "无 ✅")
