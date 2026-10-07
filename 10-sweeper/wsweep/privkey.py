# -*- coding: utf-8 -*-
"""私钥变体识别与规范化还原。

现实中同一个私钥会以多种形态散落在文件里。本模块负责：
  1. 识别 (recognize)：把任意形态的字符串解析回 32 字节原始私钥；
  2. 规范化 (canonical)：输出统一的规范形式；
  3. 变体生成 (variants)：给定私钥，枚举它所有合法写法，用于反向匹配。

覆盖的变体形态
------------------------------------------------------------------
HEX 类
  0x + 64hex            0x4c0883...318
  裸 64hex              4c0883...318
  大写 HEX              0X4C0883...318 / 4C0883...
  带空白分隔            "4c08 83a6 ... 3183 18"   (4位/8位分组)
  带连字符/冒号         4c08-83a6-... / 4c:08:...
  短于 64 位（补零）     0x4c0883... (奇数位/前置 0 省略)
  超长 hex（前导 0 填充） 0000...4c0883...
  41 + 40hex（42 位）   ★ F1-C3 拒绝 —— 这是 TRON【地址】（0x41 版本字节 + 20 字节哈希），
                        原实现会把它规范成私钥并派生出幻影地址。
  0x41 + 64hex（66 位） ★ 接受 —— 这是 TRON【私钥】的 41 前缀写法（0x41 + 32 字节），
                        由 canonical() 自产、all_variants() 自枚举。
                        ★ 与上面 42 位形态靠【长度】区分，不得靠前缀。
  WIF 类（BTC）
  压缩 WIF (K/L 开头)   L1aW4aubDFB7yfras2S1mN3anff6xvs2LQ...
  非压缩 WIF (5 开头)    5J3mBbAH58CpQ3Y5RNJpUKPE62SQ5tfcvU2Jp...
  WIF 带 0x 前缀        0xL1aW...（少见但存在）
  比特币测试网 WIF       9... / c...（testnet 前缀）
  其他
  base64 编码的 32 字节   (44 字符，含 = 填充)
  带引号/JSON 转义       "0x4c08..." , 0x4c08...\n
  TRON 私钥 64 位无前缀   4c08...（与 EVM 同一形态，无需区分）

规范化输出
------------------------------------------------------------------
  hex            : 小写 64 位，无 0x 前缀（内部存储主键）
  hex_0x         : 0x + 小写 64 位
  hex_upper      : 大写 64 位
  wif_compressed : WIF 压缩（主网）
  wif_uncompressed: WIF 非压缩（主网）
  tron           : 0x41 + 64hex（TRON 工具常见形态）
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re

import base58

from .derive import N

# --------------------------------------------------------------------------
# 变体枚举
# --------------------------------------------------------------------------
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def _norm_hex(s: str) -> str:
    """去掉所有非 hex 分隔符，返回小写 hex。"""
    return re.sub(r"[\s\-:_,]", "", s).lower()


def is_valid_privkey_int(v: int) -> bool:
    """secp256k1 私钥必须在 [1, N-1]。"""
    return isinstance(v, int) and 0 < v < N


def recognize(raw: str) -> tuple:
    """把任意形态字符串解析为 32 字节私钥。

    返回 (priv_hex_lower_64 | None, form_str, note_str)
    form 取值：hex_0x / hex_bare / hex_padded / hex_tron41 / wif_compressed /
              wif_uncompressed / base64 / None
    ★ 注（F1-C3）：hex_tron41 仅指 **66 位**（0x41 + 32 字节私钥）形态；
      42 位（0x41 + 20 字节）是 TRON【地址】，已改为拒绝，不再产出该 form。
    """
    if raw is None:
        return None, None, "空值"
    s = str(raw).strip().strip('"').strip("'").strip()
    if not s:
        return None, None, "空字符串"

    # 去掉可能包裹的括号
    s = s.strip("()[]{}<>").strip()
    if not s:
        return None, None, "空字符串"

    # ---------- base64（44 字符含 =，或 43 字符无填充）----------
    if re.fullmatch(r"[A-Za-z0-9+/]{43}=?", s) or re.fullmatch(r"[A-Za-z0-9+/]{44}", s):
        try:
            b = base64.b64decode(s + ("=" if len(s) % 4 == 3 else ""), validate=True)
            if len(b) == 32:
                v = int.from_bytes(b, "big")
                if is_valid_privkey_int(v):
                    return f"{v:064x}", "base64", "base64 的 32 字节"
        except (binascii.Error, ValueError):
            pass

    # ---------- WIF ----------
    wif_cand = s
    if wif_cand.startswith(("0x", "0X")):
        wif_cand = wif_cand[2:]
    # 主网 0x80 / 测试网 0xEF
    if re.fullmatch(r"[5KL9c][1-9A-HJ-NP-Za-km-z]{50,51}", wif_cand):
        try:
            dec = base58.b58decode_check(wif_cand)
        except ValueError:
            dec = None
        if dec is not None and len(dec) in (33, 34):
            prefix, payload = dec[0], dec[1:33]
            compressed = (len(dec) == 34 and dec[33] == 0x01)
            if prefix in (0x80, 0xEF):
                v = int.from_bytes(payload, "big")
                if is_valid_privkey_int(v):
                    if prefix == 0x80:
                        form = "wif_compressed" if compressed else "wif_uncompressed"
                        note = f"WIF 主网·{'压缩' if compressed else '非压缩'}"
                    else:
                        form = "wif_testnet_compressed" if compressed else "wif_testnet_uncompressed"
                        note = f"WIF 测试网·{'压缩' if compressed else '非压缩'}"
                    return f"{v:064x}", form, note

    # ---------- TRON 0x41 + 40hex（21 字节写法）----------
    h = s[2:] if s.startswith(("0x", "0X")) else s
    h_clean = _norm_hex(h)
    if not h_clean:
        return None, None, "无 hex 内容"

    if not re.fullmatch(r"[0-9a-f]+", h_clean):
        return None, None, "含非 hex 字符"

    # ★ 修复（F1-C3）：41 + 40hex（总长 42 位 hex）是 **TRON 地址**的 21 字节形态
    #   （0x41 是 TRON 地址版本字节 + 20 字节哈希），**不是私钥**。
    #   原实现把它 int(h_clean[2:], 16) 后左补零成 64 位 ⇒ 派生出一个幻影地址，
    #   污染"哪些私钥在手"的判断。同文件对纯 40 位 hex（EVM 地址）已正确拒绝，
    #   此处补上同等的地址识别。
    #   ★ 判据：必须靠【长度】区分，不得靠前缀 ——
    #     42 位 = 0x41 + 20 字节（地址）→ 拒绝
    #     66 位 = 0x41 + 32 字节（私钥）→ 接受，见下方分支
    if len(h_clean) == 42 and h_clean.startswith("41"):
        return None, None, "42 位 hex 是 TRON 地址（0x41 前缀 21 字节形态），非私钥"

    # TRON 0x41 前缀 + 64hex  =>  总长 66 位 hex
    # ★ F1-C3 保留本分支：这是 TRON【私钥】的 41 前缀写法，**不是地址** ——
    #   0x41 + 32 字节私钥。本模块自己的 canonical() 会产出该形态
    #   （canonical(): "tron": "41" + f"{v:064x}"），all_variants() 亦枚举它；
    #   若一并拒绝，会破坏 canonical→recognize 的自洽（实测 13 变体中 2 个无法还原）。
    #   ⇒ 与 42 位地址形态靠【长度】区分。
    if len(h_clean) == 66 and h_clean.startswith("41"):
        v = int(h_clean[2:], 16)
        if is_valid_privkey_int(v):
            return f"{v:064x}", "hex_tron41", "TRON 0x41 前缀写法（66 位：0x41 + 32 字节私钥）"

    # 标准 64
    if len(h_clean) == 64:
        v = int(h_clean, 16)
        if is_valid_privkey_int(v):
            form = "hex_0x" if s.lower().startswith("0x") else "hex_bare"
            return f"{v:064x}", form, ("0x 前缀" if form == "hex_0x" else "裸 hex")

    # 少于 64：左侧补零（常见于省略前导 0）
    # 但以下情况明确不是私钥，必须排除：
    #   · 纯数字串（id / 时间戳，如 "15245380713"）
    #   · 40 位 hex —— 这是 EVM 地址，不是私钥
    #   · 8 / 12 / 16 位等过短串 —— 多为短 ID 或截断显示
    if len(h_clean) < 64:
        if h_clean.isdigit():
            return None, None, "纯数字串，非私钥"
        if len(h_clean) == 40:
            return None, None, "40 位 hex 是 EVM 地址，非私钥"
        if len(h_clean) % 2 == 1:      # 奇数位，先补一个 0 使其成为字节对齐
            h_clean = "0" + h_clean
        # 明确要求带 0x 前缀，或长度接近 64，才认为是"省略前导零"的私钥
        has_prefix = s.lower().startswith("0x")
        if not has_prefix and len(h_clean) < 48:
            return None, None, f"过短的裸 hex（{len(h_clean)}位），不视为私钥"
        # 即使带 0x 前缀，过短（<48）也不可信 —— 那是短 ID / 地址片段
        if has_prefix and len(h_clean) < 48:
            return None, None, f"过短的 0x hex（{len(h_clean)}位），不视为私钥"
            return None, None, f"过短的裸 hex（{len(h_clean)}位），不视为私钥"
        v = int(h_clean, 16)
        if is_valid_privkey_int(v):
            return f"{v:064x}", "hex_padded", f"短 hex（{len(h_clean)}位）左补零"

    # 多于 64：仅当前导全为 0 时可还原
    if len(h_clean) > 64:
        stripped = h_clean.lstrip("0")
        if stripped and len(stripped) <= 64:
            v = int(stripped, 16)
            if is_valid_privkey_int(v):
                return f"{v:064x}", "hex_padded", f"长 hex（{len(h_clean)}位）去前导零"

    return None, None, f"无法识别（长度 {len(h_clean)}）"


def canonical(priv_hex: str) -> dict:
    """给定规范 hex（64 位小写），生成所有等价写法。"""
    v = int(priv_hex, 16)
    raw = v.to_bytes(32, "big")
    payload = b"\x80" + raw

    wif_c = base58.b58encode_check(payload + b"\x01").decode()
    wif_u = base58.b58encode_check(payload).decode()
    # 测试网
    wif_tc = base58.b58encode_check(b"\xef" + raw + b"\x01").decode()

    return {
        "hex": f"{v:064x}",
        "hex_0x": "0x" + f"{v:064x}",
        "hex_upper": f"{v:064X}",
        "hex_upper_0x": "0X" + f"{v:064X}",
        "wif_compressed": wif_c,
        "wif_uncompressed": wif_u,
        "wif_testnet_compressed": wif_tc,
        "tron": "41" + f"{v:064x}",
        "tron_0x": "0x41" + f"{v:064x}",
        "base64": base64.b64encode(raw).decode(),
    }


def all_variants(priv_hex: str) -> list:
    """返回该私钥的全部可匹配写法（去重，含大小写与分组形态）。"""
    c = canonical(priv_hex)
    out = []
    for k in ("hex", "hex_0x", "hex_upper", "hex_upper_0x", "tron", "tron_0x",
              "wif_compressed", "wif_uncompressed", "base64"):
        if c.get(k):
            out.append((k, c[k]))
    # 分组写法
    h = c["hex"]
    out.append(("hex_group4", " ".join(h[i:i + 4] for i in range(0, 64, 4))))
    out.append(("hex_group8", " ".join(h[i:i + 8] for i in range(0, 64, 8))))
    out.append(("hex_colon", ":".join(h[i:i + 2] for i in range(0, 64, 2))))
    out.append(("hex_dash", "-".join(h[i:i + 8] for i in range(0, 64, 8))))
    return out


def variant_map() -> dict:
    """返回 {写法字符串(小写): ("hex"|"wif...", 规范hex)}，供全局反查。

    注意：分组/大小写写法会归一到小写形式做键。
    """
    return {}


def build_index(priv_hexes: list) -> dict:
    """为一批私钥建立"任意写法 -> 规范 hex"的反查表。"""
    idx = {}
    for ph in priv_hexes:
        for form, text in all_variants(ph):
            idx[text.lower()] = (form, ph)
            # 无分隔符、无前缀变体也登记，便于宽松匹配
            idx[_norm_hex(text)] = (form, ph)
    return idx


def fingerprint(priv_hex: str) -> str:
    """给规范私钥一个短标识，用于日志中安全引用（不泄露私钥）。"""
    return hashlib.sha256(bytes.fromhex(priv_hex)).hexdigest()[:12]
