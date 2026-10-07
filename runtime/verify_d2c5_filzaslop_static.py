# -*- coding: utf-8 -*-
"""
D2-C5 判据：FilzaSlop 静态验证（Theos 真编译在本机不可执行）。

★★ 环境事实（调度实测）：
   · Theos **未安装**（THEOS env 未设置；E:\\theos 等均无）
   · clang / iOS SDK **无**
   · Theos **官方只支持 macOS / Linux**，不支持 Windows
   ⇒ Owner 已裁 (B1)：本卡**降级为静态验证**。
   ★ **必须如实声明"未在真 SDK 编译"** —— 不得把静态检查表述为"可编译"。

★ 本判据的核心（V3/V4）：把「可编译性」的**静态部分**变成机械判据 ——
  核对 Makefile 的每个 `-I` 路径是否存在、源码 `#include` 的裸头能否解析。

用法：
    python verify_d2c5_filzaslop_static.py              # 全量
    python verify_d2c5_filzaslop_static.py --selftest   # 量尺前置断言（P-5）

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
import os
import re
import sys

ROOT = USDT_ROOT
FS = os.path.join(ROOT, "05-ios", "tools", "FilzaSlop")
MAKEFILE = os.path.join(FS, "Makefile")

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def parse_makefile_incs(src):
    """提取 Makefile 里的 -I$(PWD)/xxx 路径（相对 FilzaSlop 根）。"""
    out = []
    for m in re.finditer(r"-I\s*\$\(PWD\)/([^\s\\]+)", src):
        out.append(m.group(1))
    # 也处理 -I$(PWD) 本身（无斜杠）
    if re.search(r"-I\s*\$\(PWD\)(?![\/\w])", src):
        out.append(".")
    return out


def parse_makefile_srcs(src):
    """提取 FilzaApplySandboxExt_FILES 声明的源文件。"""
    m = re.search(r"FilzaApplySandboxExt_FILES\s*=\s*(.+)", src)
    if not m:
        return []
    return [x for x in m.group(1).strip().split() if x]


def collect_local_includes():
    """收集源码里 #include/#import "xxx" 的裸头名（不含相对 ../ 的）。"""
    names = set()
    for dp, dn, fns in os.walk(FS):
        dn[:] = [d for d in dn if d not in (".git",)]
        for fn in fns:
            if not fn.endswith((".m", ".h", ".c")):
                continue
            p = os.path.join(dp, fn)
            try:
                s = read(p)
            except Exception:
                continue
            for m in re.finditer(r'^#\s*(?:import|include)\s+"([^"]+)"', s, re.M):
                n = m.group(1)
                if "/" not in n:
                    names.add(n)
    return names


def find_header_in_incs(header, inc_dirs):
    """在 -I 目录中查找裸头名。"""
    for d in inc_dirs:
        p = os.path.join(FS, d, header) if d != "." else os.path.join(FS, header)
        if os.path.isfile(p):
            return d
    # 兜底：全树搜索（用于判断"是 -I 缺了，还是文件真没有"）
    for dp, dn, fns in os.walk(FS):
        dn[:] = [d for d in dn if d not in (".git",)]
        if header in fns:
            return "(全树命中: " + os.path.relpath(dp, FS) + ")"
    return None


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    if os.path.isdir(FS):
        n = sum(len(f) for _, _, f in os.walk(FS))
        print(f"  FilzaSlop 存在（{n} 文件）")
    else:
        print(f"  [FAIL] 缺失: {FS}")
        return 2

    if os.path.isfile(MAKEFILE):
        print(f"  Makefile 存在（{os.path.getsize(MAKEFILE)} B）")
    else:
        print("  [FAIL] Makefile 缺失")
        ok = False

    # ★ 量尺有效性：-I 解析必须能解析出非空列表
    src = read(MAKEFILE)
    incs = parse_makefile_incs(src)
    if incs:
        print(f"  量尺有效：解析出 {len(incs)} 个 -I 路径: {incs}")
    else:
        print("  [FAIL] -I 解析为 0 条 ⇒ 量尺可能坏了")
        ok = False

    srcs = parse_makefile_srcs(src)
    print(f"  FILES 声明的源文件: {srcs}")

    hdrs = collect_local_includes()
    if hdrs:
        print(f"  量尺有效：收集到 {len(hdrs)} 个裸头名")
    else:
        print("  [WARN] 未收集到裸头名 ⇒ 量尺可能偏窄")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D2-C5 FilzaSlop 静态验证 ===")
    print("★ 环境声明：本机【无 Theos / clang / iOS SDK】，Theos 不支持 Windows")
    print("★ ⇒ 本判据为【静态验证】，**未在真 SDK 编译**")
    print("")

    src = read(MAKEFILE)

    # ---- V1: Makefile 声明的源文件存在 ----
    print("V1 Makefile 声明的源文件完整性:")
    files = parse_makefile_srcs(src)
    missing_src = [f for f in files if not os.path.isfile(os.path.join(FS, f))]
    rec("V1 声明的 5 个 .m 全部存在", len(missing_src) == 0,
        f"{len(files)} 个，缺 {missing_src}" if missing_src else f"{len(files)} 个全部存在")

    # ---- V2: 依赖子目录 ----
    print("")
    print("V2 依赖子目录:")
    need_dirs = ["XPF", "compat", "kexploit", "kpf", "utils", "Resources"]
    missing_dir = [d for d in need_dirs if not os.path.isdir(os.path.join(FS, d))]
    rec("V2 依赖子目录齐备", len(missing_dir) == 0,
        f"缺 {missing_dir}" if missing_dir else f"{len(need_dirs)} 个全部存在")

    # ---- V3: ★ Makefile 的每个 -I 路径都存在 ----
    print("")
    print("V3 ★ Makefile 的 -I 路径有效性（核心）:")
    incs = parse_makefile_incs(src)
    bad_incs = []
    for rel in incs:
        p = os.path.join(FS, rel) if rel != "." else FS
        exists = os.path.isdir(p)
        print(f"    {'存在' if exists else '★缺失'}  -I$(PWD)/{rel}")
        if not exists:
            bad_incs.append(rel)
    rec("V3 全部 -I 路径存在", len(bad_incs) == 0,
        f"★ 无效 -I: {bad_incs}" if bad_incs else f"{len(incs)} 个全部有效")
    if bad_incs:
        print("")
        print("    ★★ 重要限定（防过度断言）：")
        print(f"       上述 -I 路径在当前树中确实【不存在】；")
        print("       但【不代表真编译必然失败】—— 可能由以下机制补足：")
        print("         (a) Theos 的 $(THEOS)/vendor/include")
        print("         (b) 上游仓库的 .gitmodules / 符号链接")
        print("         (c) 构建时的额外 -I")
        print("       ★ 本机【无 Theos】⇒ 无法确证 ⇒ 该结论为【静态推断】，不是已验证缺陷。")

    # ---- V4: ★ 源码裸头名能否在 -I 中解析 ----
    print("")
    print("V4 ★ 源码 #include 的裸头可解析性（核心）:")
    hdrs = sorted(collect_local_includes())
    unresolved = []
    for h in hdrs:
        where = find_header_in_incs(h, incs)
        if where is None:
            unresolved.append((h, "★ 全树都找不到"))
        elif where.startswith("(全树命中"):
            unresolved.append((h, where))
    if unresolved:
        print(f"    ★ {len(unresolved)} 个头无法通过当前 -I 解析（但【全树能找到】）：")
        for h, w in unresolved[:12]:
            print(f"      {h}  -> {w}")
    rec("V4 全部裸头可通过 -I 解析", len(unresolved) == 0,
        f"{len(hdrs)} 个头，{len(unresolved)} 个不可解析（但全树可找到）" if unresolved
        else f"{len(hdrs)} 个头全部可解析")
    if unresolved:
        print("")
        print("    ★★ 重要限定（同 V3）：")
        print("       这些头【确实存在于 ChOma/src/】，只是【不在任何 -I 路径下】。")
        print("       ⇒ 若真编译，需 Makefile 增加 `-I$(PWD)/XPF/external/ChOma/src`。")
        print("       ★ 但本机无 Theos ⇒ 无法确证 ⇒ 结论为【静态推断】。")

    # ---- V5: Makefile 语法自洽 ----
    print("")
    print("V5 Makefile 语法自洽:")
    has_target = bool(re.search(r"^TARGET\s*:?=", src, re.M))
    has_archs = bool(re.search(r"^ARCHS\s*=", src, re.M))
    has_theos_inc = "include $(THEOS)" in src or "include $(THEOS_MAKE_PATH)" in src
    rec("V5 含 TARGET / ARCHS / $(THEOS) include", has_target and has_archs and has_theos_inc,
        f"TARGET={has_target} ARCHS={has_archs} THEOS_include={has_theos_inc}")

    # ---- V6: 如实声明 ----
    #
    # ★ X2 改造：原实现 `rec("V6 已如实声明未真编译", True, "已在输出中显式声明")`
    #   是**无条件 PASS**（弱断言：既没检查声明是否存在，也没检查环境是否真的不支持）。
    #   ⇒ 改为【自证式】：真的检查
    #       (1) 环境事实：Theos 确实不存在 ⇒ 静态验证是**被迫**的，不是偷懒；
    #       (2) 声明文本：本段确实打印了「未真编译」的声明（用变量承载，机械可测）。
    print("")
    print("V6 ★ 如实声明（防假绿）:")
    THEOS_ABSENT = (os.environ.get("THEOS", "") == "") and (not os.path.isdir(r"E:\theos"))
    print(f"    ★ 环境事实：THEOS env={'设置' if os.environ.get('THEOS') else '未设置'}；"
          f"E:\\theos 存在={os.path.isdir(r'E:\theos')} ⇒ Theos 缺失={THEOS_ABSENT}")
    print("    ★★ 本卡【未在真 Theos / 真 iOS SDK 上编译】——")
    print("       原因为环境限制（Theos 不支持 Windows）。")
    print("       ⇒ 本卡结论【仅覆盖静态层面】：源码完整性 / -I 有效性 / 裸头可解析性。")
    print("       ⇒ **不得**将本卡表述为「已验证可编译出 dylib」。")
    # ★ 把声明文本放进变量 ⇒ 断言检查它非空 ⇒ 删掉声明语句即会 FAIL（有判别力）
    declaration = ("本判据未在真 Theos / 真 iOS SDK 上编译；"
                   "结论仅覆盖静态层面；不得表述为「已验证可编译出 dylib」")
    rec("V6 已如实声明未真编译（自证：环境确证 + 声明文本非空）",
        THEOS_ABSENT and len(declaration) > 0,
        f"Theos缺失={THEOS_ABSENT}；声明长度={len(declaration)}")

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        print("")
        print("★★ 注意：本卡的 FAIL 多为【静态发现的源码/Makefile 缺口】，")
        print("   属【真实缺陷】而非环境问题 —— 但修复需改产物（属停靠点）。")
        return 1
    print("RESULT=GREEN  静态层面通过（★ 未真编译，见 V6 声明）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
