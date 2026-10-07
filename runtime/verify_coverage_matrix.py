# -*- coding: utf-8 -*-
"""
I2-C2 判据：覆盖率矩阵门禁。

断言：
  A. 矩阵文件存在且非空
  B. ★ 所有表格单元格非空（防"静默遗漏"）
  C. ★ 每个单元格必须【三态之一】：已覆盖 (...) / 未覆盖 (...) / 不适用 (...)
  D. ★ 关键维度（链 / 归集路径 / 记账路径 / region）必须被显式处理
     —— 新增维度若未登记，本判据报红
  E. ★ V0 D-4 的强制登记项必须出现且标为「未覆盖」

判据先于实现（判据 9）。本脚本放产物外（_fix_work/），不进 09-docs/cards/（P-4）。

用法：
    python verify_coverage_matrix.py              # 全量
    python verify_coverage_matrix.py --selftest   # 量尺前置断言（P-5）

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
MATRIX = os.path.join(ROOT, "09-docs", "reports", "测试覆盖率矩阵.md")

# 必须被显式处理的维度取值（新增维度时在此追加，判据会强制矩阵同步）
REQUIRED_CHAINS = ["eth", "tron", "btc", "bsc"]
REQUIRED_PATHS = ["CollectResult", "Sk()", "10-sweeper"]
REQUIRED_REGIONS = ["0 临时域", "1 公域", "2 私域"]

# V0 D-4 强制登记项（必须出现且标为未覆盖）
D4_ITEMS = [
    ("链上广播正确性", "未覆盖"),
    ("9 链签名", "未覆盖"),
    ("WASM", "未覆盖"),
    ("PM2", "未覆盖"),
    ("真机投递", "未覆盖"),
]

STATES = ("已覆盖", "未覆盖", "不适用")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def parse_table_rows(text):
    """
    返回 [(行号, [单元格...])]，仅含表格数据行。

    ★ 三态检查（C）只应作用于【数据矩阵表】，不应作用于【说明性表格】
      （如 §〇 的三态定义表、§八 的未覆盖清单）。
      首版未区分，把说明表格的内容也判为"非三态" ⇒ 138 项假红。
      判别方式：用 `<!-- MATRIX -->` 标记界定数据矩阵区间（见 MATRIX_BEGIN/END）。
    """
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") and c for c in cells):
            continue
        rows.append((i, cells))
    return rows


def matrix_data_rows(text):
    """
    仅返回【数据矩阵区间】内的表格行。
    区间由 HTML 注释标记界定：
        <!-- MATRIX-BEGIN -->  ... <!-- MATRIX-END -->
    未找到标记时返回全部表格行（并提示）。
    """
    b = text.find("<!-- MATRIX-BEGIN -->")
    e = text.find("<!-- MATRIX-END -->")
    if b < 0 or e < 0 or e <= b:
        return parse_table_rows(text), False
    seg = text[b:e]
    return parse_table_rows(seg), True


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True

    if not os.path.isfile(MATRIX):
        print(f"  [FAIL] 矩阵文件不存在: {MATRIX}")
        return 2
    print("  矩阵文件存在")

    txt = read(MATRIX)
    rows = parse_table_rows(txt)
    if len(rows) < 10:
        print(f"  [FAIL] 解析出的表格行过少 ({len(rows)}) —— 解析器可能失效")
        ok = False
    else:
        print(f"  表格解析有效：{len(rows)} 行")

    # ★ 专项：数据区间标记必须存在（C 项依赖它界定范围）
    drows, has_marker = matrix_data_rows(txt)
    if has_marker and len(drows) > 0:
        print(f"  数据区间标记有效：区间内 {len(drows)} 行")
    else:
        print("  [FAIL] 数据区间标记缺失或区间为空（C 项无法界定范围）")
        ok = False

    # 量尺：空单元格检测器必须能抓到人为制造的空格
    fake = "| a |  | c |"
    fc = [c.strip() for c in fake.strip("|").split("|")]
    if "" not in fc:
        print("  [FAIL] 空单元格检测器失效")
        ok = False
    else:
        print("  空单元格检测器有效")

    # 量尺：三态检测器
    for s, expect in (("已覆盖(MP-1)", True), ("未覆盖(原因)", True),
                      ("不适用(理由)", True), ("随便写点啥", False)):
        got = any(s.startswith(x) for x in STATES)
        if got != expect:
            print(f"  [FAIL] 三态判定错误: {s!r} -> {got}（应 {expect}）")
            ok = False
    print("  三态判定器有效")

    # ★ 专项：首列豁免必须有效 —— 首列是维度标签（`eth`/`0 临时域`），不应被三态检查
    _row = ["`eth`", "已覆盖(MP-eth)", "未覆盖(理由)", "未覆盖(理由)"]
    _bad_first = [c for c in _row if not any(c.startswith(x) for x in STATES)]
    _bad_rest = [c for c in _row[1:] if not any(c.startswith(x) for x in STATES)]
    if len(_bad_first) != 1 or len(_bad_rest) != 0:
        print(f"  [FAIL] 首列豁免失效: 全列 {len(_bad_first)} 个非三态，应仅首列 1 个")
        ok = False
    else:
        print("  首列豁免有效（维度标签不被误判）")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    fails = []
    print("=== I2-C2 覆盖率矩阵门禁 ===")
    print(f"矩阵: {MATRIX}")
    print("")

    if not os.path.isfile(MATRIX):
        print(f"  [FAIL] A: 矩阵不存在")
        print("RESULT=RED")
        return 1
    txt = read(MATRIX)

    # ---- A: 非空 ----
    if len(txt.strip()) < 500:
        print("  [FAIL] A: 矩阵内容过少")
        fails.append("A-too-short")
    else:
        print(f"  [PASS] A: 矩阵 {len(txt)} 字符")

    rows = parse_table_rows(txt)
    drows, has_marker = matrix_data_rows(txt)

    # ---- B: 无空单元格（检查全部表格行）----
    print("")
    print("B. 空单元格检查（不得留空）：")
    empties = []
    for ln, cells in rows:
        for c in cells:
            if c == "":
                empties.append(ln)
                break
    if empties:
        print(f"  [FAIL] B: {len(empties)} 行存在空单元格，行号: {empties[:10]}")
        fails.append(f"B-empty:{len(empties)}")
    else:
        print(f"  [PASS] B: {len(rows)} 行表格，无空单元格")

    # ---- C: 三态（仅检查数据矩阵区间）----
    print("")
    print("C. 三态检查（仅数据矩阵区间，每格须为 已覆盖/未覆盖/不适用）：")
    if not has_marker:
        print("  [FAIL] C: 矩阵缺少 <!-- MATRIX-BEGIN -->/<!-- MATRIX-END --> 标记，无法界定数据区间")
        fails.append("C-no-marker")
    else:
        print(f"  数据区间表格行数: {len(drows)}")
        bad = []
        for ln, cells in drows:
            # ★ 表头判定改为【结构性】，不再维护词表：
            #   若第 2 列起没有任何一格是三态 ⇒ 该行是表头（维度标签 + 列名）。
            #   首版用固定词表，新增表格（如"端到端投递用例"）会漏网 ⇒ 误报。
            rest = [c for c in cells[1:] if c not in ("", "-")]
            if rest and not any(any(c.startswith(s) for s in STATES) for c in rest):
                continue
            # ★ 首列是【维度标签】（如 `eth` / `0 临时域`），非覆盖状态
            for c in cells[1:]:
                if c in ("", "-"):
                    continue
                if not any(c.startswith(s) for s in STATES):
                    bad.append((ln, c[:50]))
        if bad:
            print(f"  [FAIL] C: {len(bad)} 个单元格不是三态:")
            for ln, c in bad[:8]:
                print(f"         行{ln}: {c!r}")
            fails.append(f"C-badstate:{len(bad)}")
        else:
            print("  [PASS] C: 数据区间内所有单元格均为三态之一")

    # ---- D: 关键维度必须被处理 ----
    print("")
    print("D. 关键维度覆盖检查（新增维度必须显式登记）：")
    for dim, items in (("链", REQUIRED_CHAINS), ("归集路径", REQUIRED_PATHS),
                       ("region", REQUIRED_REGIONS)):
        miss = [x for x in items if x not in txt]
        if miss:
            print(f"  [FAIL] D: {dim} 缺少 {miss}")
            fails.append(f"D-{dim}-{len(miss)}")
        else:
            print(f"  [PASS] D: {dim} 全部 {len(items)} 个取值已处理")

    # ---- E: D-4 强制登记项 ----
    print("")
    print("E. V0 D-4 强制登记项（须出现且标为未覆盖）：")
    for kw, need in D4_ITEMS:
        if kw not in txt:
            print(f"  [FAIL] E: 缺少 D-4 项「{kw}」")
            fails.append(f"E-missing:{kw}")
            continue
        # 检查该关键词附近有"未覆盖"
        idx = txt.find(kw)
        window = txt[max(0, idx - 120):idx + 200]
        if need in window:
            print(f"  [PASS] E: 「{kw}」已登记为未覆盖")
        else:
            print(f"  [FAIL] E: 「{kw}」未标为未覆盖（D-4 要求显式登记）")
            fails.append(f"E-not-marked:{kw}")

    print("")
    if fails:
        print(f"RESULT=RED  失败项: {fails}")
        return 1
    print("RESULT=GREEN  矩阵无空格、全三态、关键维度齐、D-4 项已登记")
    return 0


if __name__ == "__main__":
    sys.exit(main())
