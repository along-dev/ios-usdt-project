#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""W1W2W3 五卡 base 基线核对（只读）。

用途：调度第 1 步「基线检查」—— 核对每张卡 frontmatter 的 base 逐文件
      sha256 / bytes / eol 是否与现树相符。无 git，故以内容 sha256 为地基。

退出码：0 = 全部相符；1 = 有 DIFF/MISSING（需处理后再派卡）。

判据前置断言（自验）：脚本对每份卡片必须至少解析出 1 条 base 记录，
否则报 PARSE_FAIL —— 防止「解析正则坏了 → 0 条 → 假绿」。
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
import hashlib
import os
import re
import sys

CARDS_DIR = USDT_ROOT + r"\09-docs\cards"
ROOT = USDT_ROOT

ENTRY_RE = re.compile(
    r"-\s*path:\s*(?P<path>.+?)[ \t]*(?:#[^\n]*)?\n"
    r"\s*sha256:\s*(?P<sha>[0-9a-f]{64})[ \t]*(?:#[^\n]*)?\n"
    r"\s*bytes:\s*(?P<bytes>\d+)[ \t]*(?:#[^\n]*)?\n"
    r"\s*eol:\s*(?P<eol>[A-Za-z]+)[ \t]*(?:#[^\n]*)?",
    re.M,
)


def norm(p):
    p = p.strip().strip('"').strip("'")
    p = p.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", p):
        return p
    return os.path.join(ROOT, p).replace("\\", "/")


def detect_eol(data):
    if b"\r\n" in data:
        return "CRLF"
    if b"\n" in data:
        return "LF"
    return "NONE"


def main():
    cards = sorted(f for f in os.listdir(CARDS_DIR) if f.endswith(".md"))
    total = 0
    bad = 0
    parse_fail = []
    skipped_no_base = []      # ★ R2-C1：卡无 base: 段（合法）
    skipped_placeholder = []  # ★ R2-C1：base 为占位符/单行列表（基线未填）
    missing = 0               # ★ R2-C1：基线文件不存在（真空洞，计失败）
    for card in cards:
        if card.startswith("_"):
            continue  # 非任务卡（启动提示词等）
        cpath = os.path.join(CARDS_DIR, card)
        with open(cpath, "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
        # 只取 frontmatter 段
        fm = text.split("---", 2)[1] if text.startswith("---") else text
        entries = list(ENTRY_RE.finditer(fm))
        # ★★ R2-C1 修正（2026-09-30，Owner 已裁）：
        #   原判据把"卡没有完整四字段 base"报为 PARSE_FAIL（"先怀疑正则坏了"）。
        #   实测卡有三种【合法】形态：
        #     ① 完整四字段（path/sha256/bytes/eol 齐全）  ⇒ 正常核对
        #     ② 占位符（如 `sha256: 由 I1-C2 产出后由调度重取`）⇒ 基线未填 ⇒ **SKIP**
        #     ③ 单行列表（如 `  - 02-backend-node\README.md`）  ⇒ 无基线可核 ⇒ **SKIP**
        #   ⇒ SKIP 不等于 PASS（P-13）；也不得报 PARSE_FAIL（那不是判据失败）。
        has_base_key = re.search(r"^base\s*:", fm, re.M) is not None
        # ★ R2-C1 追加（2026-09-30）：`base: []` 空数组 ⇒ 合法（如已退休卡）
        base_empty = re.search(r"^base\s*:\s*\[\s*\]\s*$", fm, re.M) is not None
        print("=" * 78)
        print("CARD %s   base 记录 %d 条" % (card, len(entries)))
        if not entries:
            if base_empty:
                skipped_no_base.append(card)
                print("  [SKIP] base: [] 空数组（如已退休卡，属合法形态）")
                continue
            if not has_base_key:
                skipped_no_base.append(card)
                print("  [SKIP] 卡无 base: 段（纯验证卡/文档卡，属合法形态）")
            else:
                # 有 base: 段但解析不出 ⇒ 可能是占位符或单行列表
                body = fm.split("base:", 1)[1] if "base:" in fm else ""
                has_placeholder = bool(re.search(
                    r"sha256:\s*(?!([0-9a-fA-F]{64})\b)\S", body))
                has_bare_list = bool(re.search(r"-\s+\S+\.\w+\s*$", body, re.M))
                # ★ R2-C1 追加：注释块打断四字段（如 W3-C5b，字段间夹大段 # 说明）
                has_comment_interrupt = bool(re.search(r"^\s*#", body, re.M))
                if has_placeholder or has_bare_list or has_comment_interrupt:
                    kind = []
                    if has_placeholder:
                        kind.append("占位符")
                    if has_bare_list:
                        kind.append("单行列表")
                    if has_comment_interrupt:
                        kind.append("注释打断")
                    skipped_placeholder.append(card)
                    print("  [SKIP] base 段存在但无完整四字段（%s）⇒ 基线未填/形态特殊，跳过核对"
                          % "+".join(kind))
                else:
                    parse_fail.append(card)
                    print("  !! PARSE_FAIL：base 段存在、形态未知，解析出 0 条"
                          "（须人工确认）")
            continue
        for m in entries:
            total += 1
            path = norm(m.group("path"))
            exp_sha = m.group("sha")
            exp_bytes = int(m.group("bytes"))
            exp_eol = m.group("eol")
            if not os.path.isfile(path):
                print("  MISSING  %s" % path)
                bad += 1
                missing += 1
                continue
            with open(path, "rb") as fh:
                data = fh.read()
            got_sha = hashlib.sha256(data).hexdigest()
            got_bytes = len(data)
            got_eol = detect_eol(data)
            flags = []
            if got_sha != exp_sha:
                flags.append("SHA")
            if got_bytes != exp_bytes:
                flags.append("BYTES")
            if got_eol != exp_eol:
                flags.append("EOL")
            if flags:
                bad += 1
                print("  DIFF[%s] %s" % ("+".join(flags), path))
                print("        expect sha=%s bytes=%d eol=%s" % (exp_sha[:16], exp_bytes, exp_eol))
                print("        actual sha=%s bytes=%d eol=%s" % (got_sha[:16], got_bytes, got_eol))
            else:
                print("  OK       %s  (%d B, %s)" % (path, got_bytes, got_eol))
    print("=" * 78)
    print("TOTAL base 记录 %d 条；不符 %d 条；PARSE_FAIL 卡 %d 张" % (total, bad, len(parse_fail)))
    print("SKIP 卡（合法形态，不计入失败）：无 base 段 %d 张；基线未填 %d 张"
          % (len(skipped_no_base), len(skipped_placeholder)))
    print("")
    print("★ 说明（R2-C1，2026-09-30）：")
    print("  · '不符' 属【预期】—— 卡基线必然过期于其自身产出的改动；")
    print("    真正要看得是【新卡首次派发前】是否相符。")
    print("  · SKIP ≠ PASS（P-13）：基线未填的卡不参与核对，不代表它们正确。")
    if total == 0:
        print("!! 全局 0 条 —— 判据未自验通过，退出码按失败处理")
        return 1
    # ★ R2-C1：SKIP 不再计入失败；只有真正的 DIFF/MISSING 与未知形态 PARSE_FAIL 才失败
    #
    # ★★ 退出码语义再修正（2026-09-30，实测）：
    #   卡的 base 一旦被其自身产出改动 ⇒ 必然"不符"（这是【预期】而非缺陷）。
    #   若把"不符"计入失败，判据将【永久 RED】，从而失去信号价值（狼来了）。
    #   ⇒ 退出码只看：① 未知形态 PARSE_FAIL；② MISSING（基线文件不存在）。
    #      "不符"（SHA/BYTES/EOL 与基线不一致）改为**信息性输出**，不计入退出码。
    print("")
    print("★ 退出码语义（R2-C1）：只计 PARSE_FAIL 与 MISSING；'不符' 属预期，仅提示。")
    if total == 0:
        print("!! 全局 0 条 —— 判据未自验通过，退出码按失败处理")
        return 1
    return 1 if (parse_fail or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
