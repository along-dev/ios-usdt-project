# -*- coding: utf-8 -*-
"""D4：用 _secrethunt 的已知资产全集反向校验脱敏覆盖度。

思路（改进 N-5「自检只覆盖 6 个特征」的局限）：
    不再人工列举"应该抹除什么"，而是拿【已知资产全集】去 grep 产物，
    命中即说明该值进入了产物。

★ 安全性：本脚本只读取 assets.json，**不落地任何明文模式文件**；
  唯一输出是分类统计（指纹已截断到 24 字符）。

  ★ 补充限定（⌛2026-09-27 调度按 Owner 裁决追加；**上面一行的原有字节未动**）：
    本脚本的模式集，除 `assets.json` 的派生集之外，**另含产物外「集外凭据登记层」
    `_fix_work\\extra_credentials.json` 的手工登记**（值名 ＋ 值）——
    见下方 `EXTRA_CREDENTIALS` / `load_extra_credentials()` 与 `load_patterns()` 末尾的并入。
    ⇒ 上面「只读取 assets.json」一句**只描述数据来源**，**不表示模式集只有它**。
    ★ W1-C10（2026-09-27）：该登记层原先以 `MANUAL_EXTRA` 常量【内嵌于本文件】，
      今已【迁出】为上述 JSON（四个读取方共用一份）⇒ **本文件不再自带任何明文**，
      只【读】登记层；`:8` 的安全属性不变 —— 输出仍【只有计数与 路径:行】。

排除规则（三层，缺一即产生大量误报）：
  ① category == "false-positive"    —— 24 条 hashcat/john 自带测试向量
                                        （含 secp256k1 曲线常量 Gx/Gy/P/N，会命中任何加密库）
  ② secret 全为分隔符（─ 等）         —— 7 条被误标为 BIP39_ZH 的破折号线
  ③ secret 为代码片段                 —— 1 条被误标为 DOTENV 的 "os.environ.get("
  → 有效密钥基线 = 208 - 32 = 176 条

用法：
    $env:PYTHONIOENCODING='utf-8'
    python verify_redaction_reverse.py                  # 默认扫 E:\\USDT项目
    python verify_redaction_reverse.py -Target "E:\\x"
"""
# ★ X3：本脚本【自带】UTF-8 输出，不依赖调用方设置 PYTHONIOENCODING（P-10）
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
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
import collections
import io
import json
import os
import re
import sys

ASSETS = IOS_ROOT + r"\_secrethunt\assets.json"
SKIP_DIRS = {"node_modules", ".git", "_gopath", "_toolchain"}

# §6.3 明确要求保留 → 命中不算缺陷
REQUIRED_KEEP = ("1DECX7UIQIB", "cecd08aa6ff548c2", "mgr-admin-8bcde2021d98")

# 已知载体：命中后单独归类，不当作新缺陷
KNOWN_CARRIERS = (
    ("loader.dylib", "载荷内嵌（§8.4 不得改载荷，须打包期注入）"),
    ("corepayload.dylib", "载荷内嵌（§8.4）"),
    ("console.db", "coruna 演示夹具库（§8.1 判定可复制）"),
    (".env.example", "脱敏模板本身；命中项为无凭据内部服务名"),
)

# ★ 载体「类型」：这些类型的值必然残留在二进制载荷 / 演示夹具内，
#   故按【值】降级为"设计取舍"，不计为新缺陷。
#   与 build_unified.ps1 / acceptance_final.ps1 / sanitize_target.ps1 保持一致。
CARRIER_TYPES = {
    "ARCHIVE_7Z_PASSWORD", "BCRYPT_PASSWORD_HASH", "IMPLANT_JWT",
    "FERNET_ENCRYPTED_WEBHOOK", "ENV_SECRET_MONGO_URI", "ENV_SECRET_REDIS_URL",
    "CORUNA_COLLECT_GUARD_PASS",
}

# ★ W1-C10（2026-09-27）：集外凭据登记已收敛为【产物外一份】——
#   _fix_work\extra_credentials.json（形如 {"值名": "值"}），四个读取方共用。
#   ⇒ 本文件【不再自带任何明文】，只【读】该登记层（`load_extra_credentials()`）。
#   该登记层原为 `MANUAL_EXTRA` 常量内嵌于本文件（W1-C8 规格 5）；本卡把它迁出。
EXTRA_CREDENTIALS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra_credentials.json")


def load_extra_credentials():
    """读产物外的「集外凭据登记层」。返回 [(值名, 值)]；读不到则返回 []（并 stderr 告警）。

    ★ 语义未变：这些值【不在】assets.json 的 208 条全集内 ⇒「已知全集反查」对它们
      结构上无效，必须手工登记。登记层在【产物外】，只是把它从「内嵌 4 份」改为「共用 1 份」。
    ★ 安全属性照旧：只【读】值，输出仍【只有计数与 路径:行】，绝不含明文。
    """
    if not os.path.exists(EXTRA_CREDENTIALS):
        sys.stderr.write("!! 未找到集外凭据登记层：%s —— 集外凭据将不再被检查\n" % EXTRA_CREDENTIALS)
        return []
    with io.open(EXTRA_CREDENTIALS, encoding="utf-8") as fh:
        obj = json.load(fh)
    return [(str(k), str(v)) for k, v in obj.items() if str(v).strip()]


MANUAL_EXTRA = tuple(load_extra_credentials())


def is_dash_noise(s):
    return bool(s) and bool(re.fullmatch(r"[─—\-=_·\s]+", s))


def is_code_fragment(s):
    return bool(re.fullmatch(r"[A-Za-z_][\w.]*\(", s)) or s.strip().endswith("(")


def load_patterns():
    """返回 (patterns, stats, carrier_bytes)。patterns = [(bytes, 描述)]"""
    raw = json.load(io.open(ASSETS, encoding="utf-8"))
    stats = collections.Counter()
    pats = []
    # ★ 预扫：先收集【载体值】。必须按【值】而非按 type 判定 ——
    #   同一值可能同时挂在载体 type 与非载体 type 下（如 7z 口令既是
    #   ARCHIVE_7Z_PASSWORD，又作为 GEN_PASSWORD 出现）。
    #   详见 build_unified.ps1 的 Get-DerivedSanitizeRules 注释。
    carrier_bytes = set()
    for a in raw:
        if a.get("type") not in CARRIER_TYPES:
            continue
        for v in str(a.get("secret", "")).splitlines():
            v = v.strip()
            if len(v) >= 12:
                carrier_bytes.add(v.encode("utf-8"))

    for a in raw:
        s = str(a.get("secret", ""))
        tag = "%s/%s" % (a.get("category"), a.get("type"))
        stats["资产总数"] += 1
        if a.get("category") == "false-positive":
            stats["排除:已标误报"] += 1
            continue
        if is_dash_noise(s):
            stats["排除:分隔符噪声"] += 1
            continue
        if is_code_fragment(s):
            stats["排除:代码片段"] += 1
            continue
        if "\n" in s or "\r" in s:
            body = [l.strip() for l in s.splitlines()
                    if l.strip() and not l.lstrip().startswith("-----")]
            for i, l in enumerate(body[:3]):
                if len(l) >= 12:
                    pats.append((l.encode("utf-8"), tag))
            stats["展开:跨行资产"] += 1
            continue
        if len(s) < 12:
            stats["排除:过短(<12)"] += 1
            continue
        pats.append((s.encode("utf-8"), tag))
        stats["纳入:常规"] += 1
    # ★ 集外凭据并入（W1-C8）：与 assets.json 派生集【并集】使用；不参与载体降级判定。
    for _name, _val in MANUAL_EXTRA:
        pats.append((_val.encode("utf-8"), "集外/手工登记:%s" % _name))
        stats["纳入:集外手工"] += 1
    return pats, stats, carrier_bytes


def classify(rel, tag, fp, is_carrier_value=False):
    """返回 (bucket, label)"""
    if any(k in fp for k in REQUIRED_KEEP):
        return "keep", "§6.3 要求保留"
    if is_carrier_value:
        return "carrier", "载体值（载荷内嵌 / 演示夹具 / 无凭据服务名）"
    for base, why in KNOWN_CARRIERS:
        if rel.endswith(base):
            return "carrier", why
    if rel.startswith("09-docs/"):
        return "doc", "文档层 —— Sanitize-Text 未覆盖"
    return "code", "代码/其他产物"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-Target", default=USDT_ROOT)
    args = ap.parse_args()

    pats, stats, carrier_bytes = load_patterns()
    print("=" * 78)
    print("D4 脱敏反向校验（_secrethunt 全集 → 产物）")
    print("=" * 78)
    print("目标: %s\n" % args.Target)
    print("--- 资产集分诊 ---")
    for k in ("资产总数", "排除:已标误报", "排除:分隔符噪声", "排除:代码片段",
              "排除:过短(<12)", "展开:跨行资产", "纳入:常规", "纳入:集外手工"):
        if stats.get(k):
            print("  %-18s %d" % (k, stats[k]))
    print("  %-18s %d" % ("实际匹配模式数", len(pats)))

    rows = []
    for root, dirs, files in os.walk(args.Target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            p = os.path.join(root, fn)
            try:
                data = io.open(p, "rb").read()
            except Exception:
                continue
            rel = os.path.relpath(p, args.Target).replace("\\", "/")
            for s, tag in pats:
                if s in data:
                    rows.append((rel, tag, s[:24].decode("utf-8", "replace"),
                                 s in carrier_bytes))

    print("\n--- 命中 ---")
    print("  命中条目 %d   涉及文件 %d"
          % (len(rows), len({r[0] for r in rows})))

    buckets = collections.defaultdict(lambda: collections.defaultdict(set))
    for rel, tag, fp, is_cv in rows:
        b, _ = classify(rel, tag, fp, is_cv)
        buckets[b][tag].add(rel)

    titles = {
        "doc":     "★★ 需处置：文档层（Sanitize-Text 覆盖不全）",
        "code":    "★ 需处置：代码产物",
        "carrier": "○ 已知载体（载荷 / 夹具 / 模板，非新缺陷）",
        "keep":    "○ §6.3 要求保留",
    }
    for b in ("doc", "code", "carrier", "keep"):
        if not buckets.get(b):
            continue
        print("\n" + titles[b])
        for tag in sorted(buckets[b]):
            files = sorted(buckets[b][tag])
            print("  [%s]  %d 个文件" % (tag, len(files)))
            for f in files[:4]:
                print("        - %s" % f)
            if len(files) > 4:
                print("        ... 共 %d 个" % len(files))

    print("\n" + "=" * 78)
    print("判读要点：文档层的命中即【脱敏缺陷】；载体层的命中属【设计取舍】。")
    print("★ 真实凭据类（助记词/私钥/WIF/API key/SSH/会话）若 0 命中，")
    print("  说明『未复制』这条防线生效，而非脱敏生效 —— 两者不可混为一谈。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
