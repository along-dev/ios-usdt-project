# -*- coding: utf-8 -*-
"""R3-1 · 回归集拆分器（审核 E 的 E-02/E-03）。

★ Owner 裁决 A：把「冻结哈希守护断言」【移出】主回归集。

产出：
  1. `regression_main.txt`   —— 主回归集（无冻结哈希，可安全日常跑）
  2. `regression_guard.txt`  —— 守护检查集（含冻结哈希，按需跑）
  3. 每个脚本的分类依据（hex 数 + 是否含 FREEZE 提示词）

★ 只读产物 + 只写本目录的清单文件，【不修改任何判据脚本】。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import io
import json
import os
import re

ROOT = IOS_ROOT + r"\_integration\_fix_work"
OUT_MAIN = os.path.join(ROOT, "regression_main.txt")
OUT_GUARD = os.path.join(ROOT, "regression_guard.txt")
OUT_JSON = os.path.join(ROOT, "regression_manifest.json")

PAT_HEX = re.compile(rb"\b[0-9a-fA-F]{64}\b")
PAT_FREEZE_HINT = re.compile(
    r"(EXPECTED|BASELINE|FROZEN|FIXED|SHOULD_BE|expected_sha|baseline_sha|frozen)",
    re.I,
)

# ★ 明确排除：非判据的辅助脚本
EXCLUDE = {
    "_r31_scan.py", "_r31_split.py", "_r31_diag.py", "run_regression.py",
    "_gen_casbin_v3.py", "_r22_extract_routes.py", "_r22_compare.py",
    "_probe_c2.py", "_probe_c13.py", "_probe_rbac.py", "_fix_ptype.py",
    "_check_errors.py", "_check_gva_dist.py", "_list_models.py",
    "_t25_c6.py", "_t25_c5_test.cjs", "run_regression_v2.py",
}

# ★★★ R3-1 补充：会触发【构建/生成】的脚本 ⇒ 单独归入 build 集。
#   依据 P-38（并发构建会互相破坏 outDir）+ E-01（Go 构建约 30 分钟）
#   ⇒ 不适合日常回归，必须【隔离且串行】运行。
BUILD_HINTS = (
    "npm.cmd", "npm run", "npm ", "vite build", "go build",
    '[go_exe, "build', '[go, "build', "[go, \"build",
    "execSync(", "subprocess.run([npm",
)

def triggers_build(path):
    """判断脚本是否会执行构建命令。"""
    try:
        s = io.open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return False
    return any(h in s for h in BUILD_HINTS)

main_set = []
guard_set = []
build_set = []
manifest = []

for f in sorted(os.listdir(ROOT)):
    if not (f.startswith("verify_") or f.startswith("_verify")):
        continue
    if not f.endswith((".py", ".mjs", ".js")):
        continue
    if f in EXCLUDE:
        continue
    p = os.path.join(ROOT, f)
    try:
        raw = open(p, "rb").read()
    except Exception:
        continue
    hexes = PAT_HEX.findall(raw)
    s = raw.decode("utf-8", "replace")
    has_hint = bool(PAT_FREEZE_HINT.search(s))
    is_build = triggers_build(p)

    # ★ 优先级：build > guard > main
    #   （会构建的脚本即便无冻结哈希也不适合日常回归）
    if is_build:
        kind = "build"
    elif hexes:
        kind = "guard"
    else:
        kind = "main"

    entry = {
        "file": f,
        "hex_count": len(hexes),
        "freeze_hint": has_hint,
        "bytes": len(raw),
        "triggers_build": is_build,
        "kind": kind,
    }
    manifest.append(entry)
    {"main": main_set, "guard": guard_set, "build": build_set}[kind].append(f)

# ---- 写清单 ----
with open(OUT_MAIN, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("# R3-1 主回归集（无冻结哈希 ⇒ 可安全日常跑）\n")
    fh.write("# 共 %d 个脚本\n" % len(main_set))
    for f in main_set:
        fh.write(f + "\n")

with open(OUT_GUARD, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("# R3-1 守护检查集（含冻结 sha256 基线 ⇒ 按需跑，不参与日常回归）\n")
    fh.write("# 共 %d 个脚本\n" % len(guard_set))
    fh.write("# ★ 这些脚本内嵌【冻结哈希】：合法改动后会【假红】——\n")
    fh.write("#   属预期行为，需人工判断是【回归】还是【有意变更】。\n")
    for f in guard_set:
        fh.write(f + "\n")

OUT_BUILD = os.path.join(ROOT, "regression_build.txt")
with open(OUT_BUILD, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("# R3-1 构建集（会执行 go build / npm build ⇒ 必须【串行】且【按需】运行）\n")
    fh.write("# 共 %d 个脚本\n" % len(build_set))
    fh.write("# ★ 依据 P-38：vite build 会清空 outDir，并发构建互相破坏。\n")
    fh.write("# ★ 依据 E-01：Go 构建【冷 cache 约 30 分钟】。\n")
    fh.write("# ⇒ 【绝不可】与日常回归同时跑。\n")
    for f in build_set:
        fh.write(f + "\n")

with open(OUT_JSON, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=1)

print("=== R3-1 拆分结果（v2，三类）===")
print("  主回归集 (main)  : %d 个（无冻结哈希、不构建）" % len(main_set))
print("  守护检查集 (guard): %d 个（含冻结哈希）" % len(guard_set))
print("  构建集 (build)   : %d 个（会执行构建 ⇒ 串行）" % len(build_set))
print("  合计: %d" % (len(main_set) + len(guard_set) + len(build_set)))
print("")
print("  已写:")
print("    " + OUT_MAIN)
print("    " + OUT_GUARD)
print("    " + OUT_BUILD)
print("    " + OUT_JSON)
print("")
print("=== 构建集清单 ===")
for f in build_set:
    print("   ", f)
print("")
print("=== 主回归集（前 12）===")
for f in main_set[:12]:
    print("   ", f)
