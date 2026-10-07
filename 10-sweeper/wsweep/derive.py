# -*- coding: utf-8 -*-
"""多链地址派生：BIP39 助记词 / 原始私钥 -> EVM / TRON / BTC / Solana 地址与私钥。

设计要点：
  - 不强制依赖 bip_utils / mnemonic：能用则用，缺失时回退到内置纯 Python 实现。
  - 内置 BIP32/BIP39 实现复用自 E:\\CTF-任务\\atxok\\out\\bip39.py 的椭圆曲线与 CKD 逻辑，
    并补齐 hardened / non-hardened 两种派生（原脚本只支持 hardened）。
  - BIP39 词表优先读本地 E:\\CTF-任务\\bvs\\bvs\\apk_unpacked\\en-mnemonic-word-list.txt。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

try:
    from Crypto.Hash import keccak as _keccak_mod
except Exception:  # pragma: no cover
    _keccak_mod = None

try:
    import coincurve
except Exception:  # pragma: no cover
    coincurve = None

try:
    import nacl.signing
except Exception:  # pragma: no cover
    nacl = None

import base58

# --------------------------------------------------------------------------
# 曲线常量（secp256k1）
# --------------------------------------------------------------------------
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
G = (Gx, Gy)

BIP39_WORDLIST_CANDIDATES = [
    r"E:\CTF-任务\bvs\bvs\apk_unpacked\en-mnemonic-word-list.txt",
    r"E:\CTF-任务\bvs\bvs\bvc_apk\en-mnemonic-word-list.txt",
]

# TRON / BTC 常量
TRON_ADDR_PREFIX = 0x41
BIP32_HARDENED = 0x80000000


# --------------------------------------------------------------------------
# 内置 BIP39 词表加载
# --------------------------------------------------------------------------
def _load_wordlist() -> Optional[list]:
    for path in BIP39_WORDLIST_CANDIDATES:
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    words = [w.strip() for w in fh if w.strip()]
                if len(words) == 2048:
                    return words
            except Exception:
                continue
    return None


_WORDLIST = _load_wordlist()


# --------------------------------------------------------------------------
# 椭圆曲线基础运算（纯 Python 回退）
# --------------------------------------------------------------------------
def _inv(a: int, m: int) -> int:
    return pow(a, m - 2, m)


def _padd(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    lam = ((3 * x1 * x1) * _inv(2 * y1, P) if p1 == p2 else (y2 - y1) * _inv(x2 - x1, P)) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def _smul(k: int, pt=G):
    r = None
    a = pt
    while k:
        if k & 1:
            r = _padd(r, a)
        a = _padd(a, a)
        k >>= 1
    return r


def _pubkey_uncompressed(priv_int: int) -> bytes:
    """返回 64 字节 X||Y（无 0x04 前缀），用于 EVM 地址计算。"""
    pt = _smul(priv_int)
    if pt is None:
        raise ValueError("invalid private key produced point at infinity")
    x, y = pt
    return x.to_bytes(32, "big") + y.to_bytes(32, "big")


def _pubkey_compressed(priv_int: int) -> bytes:
    pt = _smul(priv_int)
    if pt is None:
        raise ValueError("invalid private key")
    x, y = pt
    return bytes([0x02 + (y & 1)]) + x.to_bytes(32, "big")


# --------------------------------------------------------------------------
# BIP32 / BIP39
# --------------------------------------------------------------------------
def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """BIP39：助记词 -> 64 字节 seed。NFKD 规范化 + PBKDF2-HMAC-SHA512。"""
    m = unicodedata.normalize("NFKD", mnemonic.strip())
    salt = unicodedata.normalize("NFKD", "mnemonic" + passphrase)
    return hashlib.pbkdf2_hmac("sha512", m.encode("utf-8"), salt.encode("utf-8"), 2048, 64)


def validate_mnemonic(mnemonic: str) -> tuple:
    """校验助记词。返回 (是否有效, 说明)。不依赖第三方库的完整校验和验证。"""
    words = mnemonic.strip().split()
    if len(words) not in (12, 15, 18, 21, 24):
        return False, f"词数 {len(words)} 不合法（应为 12/15/18/21/24）"
    if _WORDLIST is None:
        return True, "词表不可用，跳过逐词校验（仅校验词数）"
    bad = [w for w in words if w not in _WORDLIST]
    if bad:
        return False, f"存在非 BIP39 单词: {', '.join(bad[:5])}"
    # 校验和
    try:
        indices = [_WORDLIST.index(w) for w in words]
        bits = "".join(format(i, "011b") for i in indices)
        ent_len = len(bits) * 32 // 33
        entropy = int(bits[:ent_len], 2).to_bytes(ent_len // 8, "big")
        cs_len = len(bits) - ent_len
        expected = format(hashlib.sha256(entropy).digest()[0], "08b")[:cs_len]
        if bits[ent_len:] != expected:
            return False, "校验和不匹配"
    except Exception as exc:
        return False, f"校验失败: {exc}"
    return True, "OK"


def generate_mnemonic(strength: int = 128) -> str:
    """用本地词表生成合规助记词（仅供测试用途）。"""
    if _WORDLIST is None:
        raise RuntimeError("BIP39 词表不可用")
    ent_bits = strength
    entropy = os.urandom(ent_bits // 8)
    cs_len = ent_bits // 32
    bits = "".join(format(b, "08b") for b in entropy)
    cs = format(hashlib.sha256(entropy).digest()[0], "08b")[:cs_len]
    allbits = bits + cs
    return " ".join(_WORDLIST[int(allbits[i:i + 11], 2)] for i in range(0, len(allbits), 11))


class HDNode:
    """BIP32 扩展密钥节点（私有）。"""

    __slots__ = ("priv", "chain", "depth", "index", "parent_fp")

    def __init__(self, priv: int, chain: bytes, depth: int = 0, index: int = 0, parent_fp: bytes = b"\x00\x00\x00\x00"):
        self.priv = priv
        self.chain = chain
        self.depth = depth
        self.index = index
        self.parent_fp = parent_fp

    @classmethod
    def from_seed(cls, seed: bytes) -> "HDNode":
        I = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
        priv = int.from_bytes(I[:32], "big")
        if priv == 0 or priv >= N:
            raise ValueError("invalid master key")
        return cls(priv, I[32:])

    def fingerprint(self) -> bytes:
        import hashlib as _h
        pub = _pubkey_compressed(self.priv)
        return _h.new("ripemd160", _h.sha256(pub).digest()).digest()[:4]

    def ckd_priv(self, index: int) -> "HDNode":
        """CKDpriv：同时支持 hardened 与 normal 派生。"""
        if index >= BIP32_HARDENED:
            data = b"\x00" + self.priv.to_bytes(32, "big") + index.to_bytes(4, "big")
        else:
            data = _pubkey_compressed(self.priv) + index.to_bytes(4, "big")
        I = hmac.new(self.chain, data, hashlib.sha512).digest()
        child = (int.from_bytes(I[:32], "big") + self.priv) % N
        if child == 0:
            raise ValueError("derived zero key")
        return HDNode(child, I[32:], self.depth + 1, index, self.fingerprint())

    def derive_path(self, path: str) -> "HDNode":
        """按 BIP32 路径字符串派生，如 m/44'/60'/0'/0/0。"""
        node = self
        if not path or path.lower() in ("m", "m/"):
            return node
        for part in path.strip().split("/"):
            if part in ("", "m", "M"):
                continue
            hardened = part.endswith(("'", "h", "H"))
            num = int(part.rstrip("'hH"))
            node = node.ckd_priv(num | (BIP32_HARDENED if hardened else 0))
        return node


# --------------------------------------------------------------------------
# 地址编码
# --------------------------------------------------------------------------
def _keccak256(data: bytes) -> bytes:
    if _keccak_mod is not None:
        h = _keccak_mod.new(digest_bits=256)
        h.update(data)
        return h.digest()
    raise RuntimeError("pycryptodome (Crypto.Hash.keccak) 不可用，无法计算 EVM 地址")


def evm_address(priv_int: int) -> str:
    pub = _pubkey_uncompressed(priv_int)
    return "0x" + _keccak256(pub)[-20:].hex()


def tron_address(priv_int: int) -> str:
    """TRON：keccak256(uncompressed_pub)[-20:] 前加 0x41，再做 Base58Check。"""
    pub = _pubkey_uncompressed(priv_int)
    h = _keccak256(pub)[-20:]
    payload = bytes([TRON_ADDR_PREFIX]) + h
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58.b58encode(payload + checksum).decode()


def _hash160(data: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()


def _base58check(payload: bytes) -> str:
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58.b58encode(payload + checksum).decode()


def _bech32_polymod(values):
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_encode(hrp: str, data: list) -> str:
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    checksum = [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + "1" + "".join(BECH32_CHARSET[d] for d in data + checksum)


def _convertbits(data, frombits, tobits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    for value in data:
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (tobits - bits)) & maxv)
    return ret


def btc_addresses(priv_int: int) -> dict:
    """返回 BTC 的三种主流地址：P2PKH(legacy) / P2SH-P2WPKH / P2WPKH(bech32)。"""
    pub_c = _pubkey_compressed(priv_int)
    pub_u = _pubkey_uncompressed(priv_int)

    # P2PKH：主网版本号 0x00
    p2pkh = _base58check(b"\x00" + _hash160(pub_c))

    # P2SH-P2WPKH：redeemScript = 0x0014||hash160(pub)
    redeem = b"\x00\x14" + _hash160(pub_c)
    p2sh = _base58check(b"\x05" + _hash160(redeem))

    # P2WPKH bech32（v0 witness program）
    witprog = _hash160(pub_c)
    data = [0] + _convertbits(witprog, 8, 5)
    p2wpkh = _bech32_encode("bc", data)

    return {
        "p2pkh": p2pkh,
        "p2sh-p2wpkh": p2sh,
        "p2wpkh": p2wpkh,
        "_pubkey_compressed": pub_c.hex(),
        "_pubkey_uncompressed": pub_u.hex(),
    }


def solana_address(priv_seed: bytes) -> str:
    """Solana：seed -> ed25519 keypair -> base58(pubkey)。"""
    import nacl.signing as _signing
    seed = priv_seed[:32]
    sk = _signing.SigningKey(seed)
    return base58.b58encode(bytes(sk.verify_key)).decode()


# --------------------------------------------------------------------------
# 派生结果容器
# --------------------------------------------------------------------------
@dataclass
class DerivedAccount:
    source: str                      # 来源描述（文件/参数）
    kind: str                        # mnemonic | privkey
    label: str                       # 人类可读标签，如 m/44'/60'/0'/0/0 或 #raw
    evm_address: str = ""
    evm_privkey: str = ""
    tron_address: str = ""
    tron_privkey: str = ""
    btc: dict = field(default_factory=dict)
    btc_privkey: str = ""
    sol_address: str = ""
    sol_privkey: str = ""

    def to_dict(self, include_keys: bool = False) -> dict:
        d = {
            "source": self.source,
            "kind": self.kind,
            "label": self.label,
            "evm_address": self.evm_address,
            "tron_address": self.tron_address,
            "btc_p2pkh": self.btc.get("p2pkh", ""),
            "btc_p2sh_p2wpkh": self.btc.get("p2sh-p2wpkh", ""),
            "btc_p2wpkh": self.btc.get("p2wpkh", ""),
            "sol_address": self.sol_address,
        }
        if include_keys:
            d.update({
                "evm_privkey": self.evm_privkey,
                "tron_privkey": self.tron_privkey,
                "btc_privkey": self.btc_privkey,
                "sol_privkey": self.sol_privkey,
            })
        return d


# 各链默认 BIP44 coin type
COIN_TYPES = {"evm": 60, "tron": 195, "btc": 0, "sol": 501}


def accounts_from_mnemonic(
    mnemonic: str,
    source: str = "inline",
    count: int = 5,
    chains: tuple = ("evm", "tron", "btc", "sol"),
    passphrase: str = "",
    account_index: int = 0,
) -> list:
    """从助记词派生多链账户。

    每个链使用其标准 BIP44 路径，派生 count 个地址（index 0..count-1）：
      EVM   m/44'/60'/0'/0/{i}
      TRON  m/44'/195'/0'/0/{i}
      BTC   m/44'/0'/0'/0/{i}
      SOL   m/44'/501'/{i}'/0'
    """
    ok, why = validate_mnemonic(mnemonic)
    if not ok:
        raise ValueError(f"助记词校验失败: {why}")
    seed = mnemonic_to_seed(mnemonic, passphrase)
    master = HDNode.from_seed(seed)
    out = []

    for i in range(count):
        acc = DerivedAccount(source=source, kind="mnemonic", label=f"acct{account_index}/idx{i}")
        if "evm" in chains:
            node = master.derive_path(f"m/44'/60'/{account_index}'/0/{i}")
            acc.evm_privkey = f"{node.priv:064x}"
            acc.evm_address = evm_address(node.priv)
        if "tron" in chains:
            node = master.derive_path(f"m/44'/195'/{account_index}'/0/{i}")
            acc.tron_privkey = f"{node.priv:064x}"
            acc.tron_address = tron_address(node.priv)
        if "btc" in chains:
            node = master.derive_path(f"m/44'/0'/{account_index}'/0/{i}")
            acc.btc_privkey = f"{node.priv:064x}"
            acc.btc = btc_addresses(node.priv)
        if "sol" in chains:
            node = master.derive_path(f"m/44'/501'/{i}'/0'")
            # Solana 用 seed 本身的 32 字节做 ed25519 私钥
            acc.sol_privkey = node.priv.to_bytes(32, "big").hex()
            acc.sol_address = solana_address(node.priv.to_bytes(32, "big"))
        out.append(acc)
    return out


def account_from_privkey(raw: str, source: str = "inline", chains: tuple = ("evm", "tron", "btc", "sol")) -> DerivedAccount:
    """从原始私钥构造账户。支持 0x 前缀 / 裸 hex / WIF（BTC）。"""
    raw = raw.strip()
    acc = DerivedAccount(source=source, kind="privkey", label="#raw")

    priv_int = None
    # 尝试 BTC WIF（Base58Check，长度 51/52）
    if len(raw) in (51, 52) and not raw.startswith("0x"):
        try:
            decoded = base58.b58decode_check(raw)
            if len(decoded) == 33 and decoded[0] in (0x80, 0xEF):
                priv_int = int.from_bytes(decoded[1:33], "big")
        except Exception:
            pass

    if priv_int is None:
        h = raw[2:] if raw.startswith(("0x", "0X")) else raw
        if len(h) == 64:
            try:
                priv_int = int(h, 16)
            except ValueError:
                raise ValueError(f"无法解析为私钥: {raw[:12]}...")
        elif len(h) == 66 and h.startswith("41"):
            # TRON 私钥常以 41 前缀出现（实际应为 32 字节）
            try:
                priv_int = int(h[2:], 16)
            except ValueError:
                raise ValueError("TRON 私钥解析失败")
        else:
            raise ValueError(f"私钥长度不合法（{len(h)} hex 字符）")

    if priv_int is None or not (0 < priv_int < N):
        raise ValueError("私钥超出 secp256k1 有效范围")

    if "evm" in chains:
        acc.evm_privkey = f"{priv_int:064x}"
        acc.evm_address = evm_address(priv_int)
    if "tron" in chains:
        acc.tron_privkey = f"{priv_int:064x}"
        acc.tron_address = tron_address(priv_int)
    if "btc" in chains:
        acc.btc_privkey = f"{priv_int:064x}"
        acc.btc = btc_addresses(priv_int)
    if "sol" in chains:
        # 原始私钥无法直接映射到 ed25519；用同一 32 字节种子派生（仅作占位）
        seed = priv_int.to_bytes(32, "big")
        acc.sol_privkey = seed.hex()
        acc.sol_address = solana_address(seed)
    return acc
