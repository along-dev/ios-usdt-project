# -*- coding: utf-8 -*-
"""
D0-C2b 判据：脱敏通道「正则模式集」扩展。

★ P-4 自指防护：本脚本【不硬编码任何 key 值】，只用正则匹配形态。
★ P-5 量尺前置断言：R3 正向命中 与 R4 反向不误伤【成对】存在。

用法：
    python verify_d0c2b_apikey_patterns.py              # 全量（R1-R6）
    python verify_d0c2b_apikey_patterns.py --selftest   # 只跑量尺前置断言

退出码：0 = 全绿；非 0 = 有红。
"""
from __future__ import annotations

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import json
import os
import re
import subprocess
import sys

BUILD = IOS_ROOT + r"\_integration\build_unified.ps1"
FIXDIR = IOS_ROOT + r"\_integration\_fix_work"
PATTERNS_JSON = os.path.join(FIXDIR, "api_key_patterns.json")
ANKR_VERIFIER = os.path.join(FIXDIR, "verify_d0c2_ankr_key.py")
LEGACY_JSON = os.path.join(FIXDIR, "legacy_replacement_patterns.json")

_results = []


def rec(name, ok, detail):
    _results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def read_bytes(path):
    """★ 二进制模式读取：文本模式会做换行转换，导致 eol/字节计数失真。"""
    with open(path, "rb") as f:
        return f.read()


def decode(raw):
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8", errors="replace")


def load_patterns():
    if not os.path.isfile(PATTERNS_JSON):
        return [], "登记件不存在"
    try:
        doc = json.loads(decode(read_bytes(PATTERNS_JSON)))
    except Exception as e:
        return [], f"解析失败: {e}"
    if not isinstance(doc, list):
        return [], "根节点不是【有序数组】"
    out = []
    for e in doc:
        if not isinstance(e, dict):
            continue
        pat = str(e.get("pattern") or "")
        ph = str(e.get("placeholder") or "")
        if not pat.strip() or not ph.strip():
            continue
        out.append({"pattern": pat, "placeholder": ph,
                    "note": str(e.get("note") or "")})
    return out, None


def extract_function(src, name):
    """从 ps1 源码抽出 function Name { ... 配对花括号 的函数体。"""
    m = re.search(r"(?m)^[ \t]*function\s+" + re.escape(name) + r"\s*\{", src)
    if not m:
        return None
    start = m.start()
    i = src.index("{", m.start())
    depth = 0
    while i < len(src):
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    return None


def run_ps(script, timeout=180):
    """跑 PowerShell 5.1（★ UTF-8 BOM，否则 PS 5.1 按 ANSI 读中文解析错）。"""
    p = os.path.join(FIXDIR, "_d0c2b_tmp.ps1")
    with open(p, "wb") as f:
        f.write(b"\xef\xbb\xbf" + script.encode("utf-8"))
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", p],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -999, "", "超时"
    finally:
        try:
            os.remove(p)
        except OSError:
            pass


def extract_braced_block(src, head_re):
    """
    ★ 花括号配平式抽取：从 head_re 匹配到的 `{` 起，数到配对 `}` 为止。
      不能用 `.*?\\n[ \\t]*\\}` 懒匹配 —— 内层 `}` 会把块【截断】
      （本脚本首版即踩此坑：夹具报 "Missing closing '}'"）。
    """
    m = re.search(head_re, src, re.S)
    if not m:
        return None
    i = src.index("{", m.start())
    depth = 0
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():i + 1]
        i += 1
    return None


def build_channel_harness(src):
    """★ 引用【真实脚本代码】抽出两条通道块，避免自证。"""
    sanitize_fn = extract_function(src, "Sanitize-Text")
    if sanitize_fn is None:
        return None, False, "未能从 build_unified.ps1 抽出 Sanitize-Text 函数"

    literal_block = extract_braced_block(
        sanitize_fn,
        r"foreach\s*\(\s*\$kv\s+in\s+\$SANITIZE_REPLACEMENTS\.GetEnumerator\(\)\s*\)")
    regex_block = extract_braced_block(
        sanitize_fn,
        r"foreach\s*\(\s*\$[A-Za-z_]*\s+in\s+\$SANITIZE_APIKEY_PATTERNS\s*\)")

    if literal_block is None:
        return None, False, "未能抽出【字面通道】循环"
    if regex_block is None:
        return None, False, "未能抽出【正则通道】循环（R1 未落地）"
    return (literal_block, regex_block), True, "ok"


def ps_lit(s):
    """PowerShell【单引号】字面量：内部单引号翻倍。避免 $ / ${} 被当变量展开。"""
    return "'" + str(s).replace("'", "''") + "'"


def indent(block, n=2):
    pad = " " * n
    return "\n".join(pad + ln for ln in block.splitlines())


def ps_harness(literal_pairs, patterns, samples):
    # ★ PS 字面量必须用【单引号】：占位符形如 ${JWT_SECRET}，
    #   在 PowerShell 双引号中会被当【变量引用】解析 ⇒ 展开成空串
    #   （真脚本 L140 已就此踩坑并注明；本判据夹具同坑）。
    lit_lines = []
    for k, v in literal_pairs:
        lit_lines.append(
            "$SANITIZE_REPLACEMENTS[" + ps_lit(k) + "] = " + ps_lit(v))
    pat_lines = []
    for p in patterns:
        pat_lines.append(
            "$SANITIZE_APIKEY_PATTERNS += [pscustomobject]@{ "
            "Pattern = " + ps_lit(p['pattern']) + "; "
            "Placeholder = " + ps_lit(p['placeholder']) + " }")
    # ★ 样本经【JSON 文件】注入，不内联进脚本：
    #   Python json.dumps 产出的 \" 在 PowerShell 里是转义引号 ⇒ 字符串被截断
    #   （本脚本首版即踩此坑：输出退化为 `const u = \`）。
    #   改为写 UTF-8 JSON、由 PS 用 ConvertFrom-Json 读回 ⇒ 无转义歧义。
    samples_file = os.path.join(FIXDIR, "_d0c2b_samples.json")
    with open(samples_file, "wb") as f:
        f.write(json.dumps(samples, ensure_ascii=False).encode("utf-8"))
    # ★ 路径用【PowerShell 单引号字面量】注入，绝不能用 json.dumps：
    #   后者把非 ASCII 转成 \uXXXX，而 PowerShell 不解析 \u 转义
    #   ⇒ 路径退化为 'E:\ios\u6f0f\u6d1e\...'（本脚本第二版即踩此坑）。
    ps_path = "'" + samples_file.replace("'", "''") + "'"
    body = [
        "  $__samples = Get-Content -Path "
        + ps_path + " -Raw -Encoding UTF8 | ConvertFrom-Json",
        "  foreach ($__s in $__samples) {",
        "    $r = Sanitize-Text-Inline -text ([string]$__s.text)",
        '    Write-Output ("@@" + $__s.id + "|" + $r.LiteralHits + "|" + $r.RegexHits + "|" + $r.Text)',
        "  }",
    ]
    return "\n".join([
        "$ErrorActionPreference = 'Stop'",
        "$SANITIZE_REPLACEMENTS = [ordered]@{}",
        "\n".join(lit_lines),
        "$SANITIZE_APIKEY_PATTERNS = @()",
        "\n".join(pat_lines),
        "function Sanitize-Text-Inline {",
        "  param([string]$text)",
        "  $before = 0",
        indent("__LITERAL_BLOCK__"),
        "  $apiBefore = 0",
        indent("__REGEX_BLOCK__"),
        "  return [pscustomobject]@{ Text = $text; LiteralHits = $before; RegexHits = $apiBefore }",
        "}",
        "\n".join(body),
    ])


def check_r1(src):
    print("")
    print("R1 build_unified.ps1 含【正则模式通道】:")
    has_replace = "[regex]::Replace" in src
    has_var = re.search(r"\$SANITIZE_APIKEY_PATTERNS\b", src) is not None
    has_load = "api_key_patterns.json" in src
    has_loud = re.search(r"\$SANITIZE_APIKEY_VALID\s*-eq\s*0", src) is not None
    rec("R1 含正则模式通道",
        has_replace and has_var and has_load and has_loud,
        f"[regex]::Replace={has_replace} 模式表={has_var} "
        f"载入登记件={has_load} 缺失响亮失败={has_loud}")

    # ★ 位置判定必须限定在【Sanitize-Text 函数体内】：
    #   全局 find 会先撞上文件上方【登记件加载段】对 $SANITIZE_APIKEY_PATTERNS 的引用，
    #   从而误判"正则通道在字面通道之前"（本脚本首版即踩此坑）。
    fn = extract_function(src, "Sanitize-Text") or ""
    pos_lit = fn.find("foreach ($kv in $SANITIZE_REPLACEMENTS.GetEnumerator())")
    pos_rgx = fn.find("foreach ($__pat in $SANITIZE_APIKEY_PATTERNS)")
    in_order = (pos_lit != -1 and pos_rgx != -1 and pos_rgx > pos_lit)
    rec("R1b 正则通道在【字面通道之后】执行", in_order,
        f"函数体内 字面@{pos_lit} 正则@{pos_rgx}（须 正则 > 字面，且均 != -1）")


def check_r2(entries, err):
    print("")
    print("R2 模式登记件 api_key_patterns.json:")
    if err:
        rec("R2 登记件存在且有效条目>=1", False, f"★ {err}")
        return
    rec("R2 登记件存在且有效条目>=1", len(entries) >= 1,
        f"有效条目 {len(entries)} 条")
    for e in entries:
        print(f"      · {e['note'] or '(无说明)'}  ->  {e['placeholder']}")


def check_r5(src):
    print("")
    print("R5 既有【字面通道】行为不变:")
    channels, ok, note = build_channel_harness(src)
    if not ok:
        rec("R5 字面通道行为不变", False, f"★ {note}")
        return
    literal_block, regex_block = channels

    try:
        doc = json.loads(decode(read_bytes(LEGACY_JSON)))
        legacy = [(str(e["value"]), str(e["placeholder"]))
                  for e in doc if str(e.get("value", "")).strip()]
    except Exception as e:
        rec("R5 字面通道行为不变", False, f"读既有登记件失败: {e}")
        return
    if not legacy:
        rec("R5 字面通道行为不变", False, "既有登记件无有效条目")
        return

    val, ph = legacy[0]
    sample = f'const k = "{val}";'
    script = ps_harness(legacy, [], [{"id": "lit", "text": sample}])
    script = script.replace("__LITERAL_BLOCK__", indent(literal_block))
    script = script.replace("__REGEX_BLOCK__", indent(regex_block))
    code, out, errout = run_ps(script)
    if code != 0:
        rec("R5 字面通道行为不变", False,
            f"夹具 EXIT={code} {errout.strip()[:200]}")
        return

    hit = re.search(r"@@lit\|(\d+)\|(\d+)\|", out)
    replaced = f'const k = "{ph}";' in out
    lh = int(hit.group(1)) if hit else -1
    rh = int(hit.group(2)) if hit else -1
    rec("R5 字面通道行为不变（字面键仍被替换）",
        lh >= 1 and replaced,
        f"字面命中={lh} 正则命中={rh} 已替换为占位符={replaced}")
    rec("R5b 正则通道不触碰字面键（空模式表时命中=0）", rh == 0,
        f"正则命中={rh}（须 0）")


def hexs(n, ch="a"):
    return ch * n


def check_r3_r4(src, entries):
    print("")
    print("R3 正向：合成样本【必须被命中并替换】:")
    print("R4 反向：正常 URL / 交易哈希【不得被替换】:")

    if not entries:
        rec("R3 正向命中", False, "无有效模式条目 => 无法正向（P-5：先怀疑模式坏了）")
        rec("R4 反向不误伤", False, "无有效模式条目 => 无法反向")
        return

    channels, ok, note = build_channel_harness(src)
    if not ok:
        rec("R3 正向命中", False, f"★ {note}")
        rec("R4 反向不误伤", False, f"★ {note}")
        return
    literal_block, regex_block = channels

    pos = [
        ("std-eth", 'const u = "https://rpc.ankr.com/eth/' + hexs(64) + '";'),
        ("std-bsc", 'const u = "https://rpc.ankr.com/bsc/' + hexs(64, "b") + '";'),
        ("premium", 'const u = "https://rpc.ankr.com/premium-http/eth/' + hexs(64, "c") + '";'),
        ("len32", 'const u = "https://rpc.ankr.com/polygon/' + hexs(32, "d") + '";'),
    ]
    neg = [
        ("nokey-root", 'const u = "https://rpc.ankr.com/";'),
        ("nokey-chain", 'const u = "https://rpc.ankr.com/eth";'),
        ("txhash-0x64", 'const txHash = "0x' + hexs(64, "e") + '";'),
        ("addr-0x40", 'const addr = "0x' + hexs(40, "f") + '";'),
        ("plain-url", 'const u = "https://example.com/api/v1/status";'),
    ]
    all_s = [{"id": i, "text": t} for i, t in (pos + neg)]
    script = ps_harness([], entries, all_s)
    script = script.replace("__LITERAL_BLOCK__", indent(literal_block))
    script = script.replace("__REGEX_BLOCK__", indent(regex_block))

    code, out, errout = run_ps(script)
    if code != 0:
        rec("R3 正向命中", False, f"夹具 EXIT={code} {errout.strip()[:200]}")
        rec("R4 反向不误伤", False, f"夹具 EXIT={code} {errout.strip()[:200]}")
        return

    got = {}
    for line in out.splitlines():
        if line.startswith("@@"):
            parts = line[2:].split("|", 3)
            if len(parts) == 4:
                got[parts[0]] = (int(parts[2]), parts[3])

    print("    ★ 正向样本（替换前 -> 替换后）:")
    pos_ok = True
    for sid, before in pos:
        hits, after = got.get(sid, (-1, ""))
        hitok = hits >= 1 and "<REDACTED" in after
        pos_ok = pos_ok and hitok
        print(f"      [{sid}] 前: {before}")
        print(f"      [{sid}] 后: {after}   (正则命中={hits})")
    rec("R3 ★ 正向：合成 Ankr key 被命中并替换", pos_ok,
        f"{sum(1 for s, _ in pos if '<REDACTED' in got.get(s, (0, ''))[1])}"
        f"/{len(pos)} 命中")

    print("")
    print("    ★ 反向样本（必须保持原样）:")
    neg_ok = True
    for sid, before in neg:
        hits, after = got.get(sid, (-1, ""))
        unchanged = (after == before)
        neg_ok = neg_ok and unchanged and hits == 0
        print(f"      [{sid}] {after}   (正则命中={hits}, 未变={unchanged})")
    rec("R4 ★ 反向：无 key URL / 交易哈希 / 普通 URL 不被误伤", neg_ok,
        f"{sum(1 for s, b in neg if got.get(s, (-1, ''))[1] == b)}"
        f"/{len(neg)} 未被替换")


def check_r6():
    print("")
    print("R6 verify_d0c2_ankr_key.py 须转绿:")
    if not os.path.isfile(ANKR_VERIFIER):
        rec("R6 ankr_key 判据 A5 转绿", False, "判据件不存在")
        return
    r = subprocess.run([sys.executable, ANKR_VERIFIER, "--skip-go"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=FIXDIR)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"=== (\d+)/(\d+) 通过 ===", out)
    a5 = "[PASS] A5" in out
    passed = int(m.group(1)) if m else -1
    total = int(m.group(2)) if m else -1
    tail = "\n".join(out.strip().splitlines()[-16:])
    print("    " + tail.replace("\n", "\n    "))
    rec("R6 A5 转绿（脱敏模式集已含 API key 类）", a5,
        f"{passed}/{total} 通过；A5={'PASS' if a5 else 'FAIL'}")
    rec("R6 ankr_key 判据 7/7（--skip-go 口径；A6 编译门单独跑）",
        passed == 7 and total == 7, f"{passed}/{total}")


def selftest():
    print("=== 量尺前置断言（P-5）===")
    ok = True
    entries, err = load_patterns()
    if err:
        print(f"  [FAIL] 登记件不可用: {err}")
        return 2
    print(f"  登记件有效条目 {len(entries)} 条")

    probe = 'const u = "https://rpc.ankr.com/eth/' + hexs(64) + '";'
    if any(re.search(e["pattern"], probe) for e in entries):
        print("  正向探针命中（模式未坏）")
    else:
        print("  [FAIL] ★ 无任何模式能在 Ankr 正例上命中 —— 先怀疑模式坏了")
        ok = False

    for label, txt in (("无 key URL", 'const u = "https://rpc.ankr.com/";'),
                       ("交易哈希", "0x" + hexs(64, "e"))):
        bad = [e["note"] for e in entries if re.search(e["pattern"], txt)]
        if bad:
            print(f"  [FAIL] ★ 模式误命中{label}: {bad}")
            ok = False
        else:
            print(f"  反向探针正确：{label} 不命中")

    me = open(os.path.abspath(__file__), encoding="utf-8",
              errors="replace").read()
    if re.search(r"rpc\.ankr\.com/[^\"'\s]*[0-9a-f]{32,}", me):
        print("  [FAIL] ★ 本判据脚本自身含 key 明文（P-4）")
        ok = False
    else:
        print("  P-4 自指防护有效：本脚本不含 key 明文")

    print("SELFTEST=OK" if ok else "SELFTEST=BAD")
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    print("=== D0-C2b 脱敏模式集扩展判据 ===")
    print(f"脚本  : {BUILD}")
    print(f"登记件: {PATTERNS_JSON}")

    if not os.path.isfile(BUILD):
        print("  [FAIL] build_unified.ps1 不存在")
        return 1
    src = decode(read_bytes(BUILD))
    entries, err = load_patterns()

    check_r1(src)
    check_r2(entries, err)
    check_r5(src)
    check_r3_r4(src, entries)
    check_r6()

    print("")
    fails = [r for r in _results if not r["ok"]]
    print(f"=== {len(_results) - len(fails)}/{len(_results)} 通过 ===")
    if fails:
        print(f"RESULT=RED  {len(fails)} 项失败:")
        for f in fails:
            print(f"  - {f['name']}: {f['detail']}")
        return 1
    print("RESULT=GREEN  正则通道已落地：正向命中、反向不误伤、字面通道行为未变")
    return 0


if __name__ == "__main__":
    sys.exit(main())