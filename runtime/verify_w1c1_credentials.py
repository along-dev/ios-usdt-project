# -*- coding: utf-8 -*-
"""W1-C10 判据：产物内不得残留【集外凭据登记层】里的那些值。

★ 登记层（★ 在产物外）：`_fix_work\\extra_credentials.json`，形如 {"值名": "值"}。
  本脚本【不自带任何明文】，只【读】它 —— 四读取方共用一份
  （build_unified.ps1 / acceptance_final.ps1 / verify_redaction_reverse.py / 本脚本）。
  ⇒ 下次发现新值时【只改一处】。

★ 为什么这个脚本在 _fix_work 而不在 09-docs/cards/：
  它【读】的这些值若落在产物内即成为泄漏点（与「缺陷 C：定义检测模式的文档本身在产物内」
  是同一类自指）⇒ 登记层与判据都必须在【产物外】。

★ 这些值的特殊性（决定了 D4 覆盖不到它们）：
  它们**不在** `_secrethunt\assets.json` 的 208 条资产集内。
  即「用已知全集反查」的方法对它们**结构上无效** —— 必须手工登记。
  （2026-09-27 实测确认）

用法：
    $env:PYTHONIOENCODING='utf-8'
    python verify_w1c1_credentials.py                 # 默认扫 E:\\USDT项目
    python verify_w1c1_credentials.py -Target <dir>
退出码：0 = 全部 0 命中；1 = 有残留；2 = 登记层不可读 / 目标不存在
"""
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
import io
import json
import os
import sys

# ★ 集外凭据登记层（产物外；四个读取方共用）。本脚本只【读】它。
EXTRA_CREDENTIALS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra_credentials.json")


def load_patterns():
    """读「集外凭据登记层」→ {值名: 值}。
    ★ 读不到就【响亮返回空】—— 绝不在脚本内保留明文兜底（否则登记层形同虚设）。"""
    if not os.path.exists(EXTRA_CREDENTIALS):
        sys.stderr.write("!! 未找到集外凭据登记层：%s\n" % EXTRA_CREDENTIALS)
        return {}
    with io.open(EXTRA_CREDENTIALS, encoding="utf-8") as fh:
        obj = json.load(fh)
    return {str(k): str(v) for k, v in obj.items() if str(v).strip()}


PATTERNS = load_patterns()
SKIP_DIRS = {"node_modules", ".git", "_gopath", "_toolchain"}


def meter_selfcheck():
    """★ 量尺前置断言：先证明模式能命中，否则「0 命中」可能只是模式写错了。
    本轮已踩过同类（grep 未锚定 .js$、模式被反引号截断）。"""
    ok = True
    for name, pat in PATTERNS.items():
        sample = "prefix-" + pat + "-suffix"
        if pat not in sample:
            print("  ✗ 量尺自检失败: %s 的模式在其自身样本中都不命中" % name)
            ok = False
    if ok:
        print("  量尺自检: %d 个模式均能在样本中命中 ✓" % len(PATTERNS))
    return ok


def scan(target):
    hits = {}
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            p = os.path.join(root, fn)
            try:
                data = io.open(p, "rb").read()
            except Exception:
                continue
            rel = os.path.relpath(p, target).replace("\\", "/")
            for name, pat in PATTERNS.items():
                if pat.encode("utf-8") in data:
                    hits.setdefault(name, []).append(rel)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-Target", default=USDT_ROOT)
    args = ap.parse_args()

    print("=" * 74)
    print("集外凭据判据：产物内残留的「集外凭据」（登记层驱动）")
    print("=" * 74)
    print("目标: %s\n" % args.Target)
    print("登记层: %s（%d 条）\n" % (EXTRA_CREDENTIALS, len(PATTERNS)))

    if not PATTERNS:
        print("结论: ✗ 登记层不可读或为空 —— 本判据不可用（不以「0 命中」蒙混）")
        return 2

    print("--- 量尺前置断言 ---")
    if not meter_selfcheck():
        print("\n结论: ✗ 量尺本身坏了，本次结果不可用")
        return 1

    print("\n--- 扫描 ---")
    if not os.path.isdir(args.Target):
        print("目标不存在: %s" % args.Target)
        return 2
    hits = scan(args.Target)

    total = sum(len(v) for v in hits.values())
    for name in PATTERNS:
        fs = hits.get(name, [])
        if fs:
            print("  ✗ [%s] 残留 %d 处:" % (name, len(fs)))
            for f in fs[:8]:
                print("        - %s" % f)
            if len(fs) > 8:
                print("        ... 共 %d 个文件" % len(fs))
        else:
            print("  OK [%s] 0 命中" % name)

    print("\n" + "=" * 74)
    if total:
        print("结论: ✗ 仍有 %d 处残留 —— 未通过" % total)
        return 1
    print("结论: ✓ 登记层内 %d 个集外凭据在产物内 0 命中" % len(PATTERNS))
    print()
    print("注：本判据只覆盖【登记层 _fix_work\\extra_credentials.json 内已登记的值】。")
    print("    真实凭据全集未知，「0 命中」不代表产物无其他泄漏。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
