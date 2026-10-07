# -*- coding: utf-8 -*-
"""BTC 交易构造与签名（P2WPKH / P2PKH）。

实现 BIP143（segwit v0）签名哈希与 ECDSA 签名，使用环境已有的 coincurve。
仅用于把单个地址的全部余额扫到目标地址（sweep）。
"""
from __future__ import annotations

import hashlib
import struct

import base58

from .derive import _pubkey_compressed, _hash160, _base58check, _bech32_encode, _convertbits
from . import chains as C

try:
    import coincurve
except Exception:  # pragma: no cover
    coincurve = None

SIGHASH_ALL = 1
DUST_LIMIT = 546


# --------------------------------------------------------------------------
# 交易序列化
# --------------------------------------------------------------------------
def _varint(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", n)
    if n <= 0xFFFFFFFF:
        return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)


def _ser_tx(version, inputs, outputs, locktime=0, segwit=False, witnesses=None) -> bytes:
    """序列化交易。inputs: [(txid_hex, vout, scriptSig, sequence)]"""
    out = struct.pack("<i", version)
    if segwit:
        out += b"\x00\x01"  # marker + flag
    out += _varint(len(inputs))
    for txid, vout, script_sig, seq in inputs:
        out += bytes.fromhex(txid)[::-1]          # 小端
        out += struct.pack("<I", vout)
        out += _varint(len(script_sig)) + script_sig
        out += struct.pack("<I", seq)
    out += _varint(len(outputs))
    for value, spk in outputs:
        out += struct.pack("<Q", value)
        out += _varint(len(spk)) + spk
    if segwit and witnesses is not None:
        for w in witnesses:
            out += _varint(len(w))
            for item in w:
                out += _varint(len(item)) + item
    out += struct.pack("<I", locktime)
    return out


def _spk_p2wpkh(pubkey: bytes) -> bytes:
    return b"\x00\x14" + _hash160(pubkey)


def _spk_p2pkh(pubkey: bytes) -> bytes:
    return b"\x76\xa9\x14" + _hash160(pubkey) + b"\x88\xac"


# --------------------------------------------------------------------------
# BIP143 sighash
# --------------------------------------------------------------------------
def _bip143_sighash(inputs, outputs, index, prevout_value, prevout_spk,
                    pubkey, hash_type=SIGHASH_ALL) -> bytes:
    """BIP143 签名哈希（segwit v0）。"""
    hash_prevouts = hashlib.sha256(
        hashlib.sha256(b"".join(
            bytes.fromhex(txid)[::-1] + struct.pack("<I", vout)
            for txid, vout, _, _ in inputs)).digest()).digest()
    hash_sequence = hashlib.sha256(
        hashlib.sha256(b"".join(struct.pack("<I", seq) for _, _, _, seq in inputs)).digest()
    ).digest()
    hash_outputs = hashlib.sha256(
        hashlib.sha256(b"".join(
            struct.pack("<Q", v) + _varint(len(spk)) + spk
            for v, spk in outputs)).digest()).digest()

    txid, vout, _, seq = inputs[index]
    preimage = (
        struct.pack("<i", 2)
        + hash_prevouts + hash_sequence
        + bytes.fromhex(txid)[::-1] + struct.pack("<I", vout)
        + _varint(len(prevout_spk)) + prevout_spk
        + struct.pack("<Q", prevout_value)
        + struct.pack("<I", seq)
        + hash_outputs
        + struct.pack("<I", 0)
        + struct.pack("<I", hash_type)
    )
    return hashlib.sha256(hashlib.sha256(preimage).digest()).digest()


def _bip143_sighash_p2sh_p2wpkh(inputs, outputs, index, prevout_value, pubkey,
                                hash_type=SIGHASH_ALL) -> bytes:
    """P2SH-P2WPKH：scriptCode 为 P2PKH 脚本，其余同 BIP143。"""
    return _bip143_sighash(inputs, outputs, index, prevout_value,
                           _spk_p2pkh(pubkey), pubkey, hash_type)


def _sign(priv_int: int, digest: bytes, hash_type=SIGHASH_ALL) -> bytes:
    """ECDSA 签名，返回 DER 编码 + hash_type 字节。"""
    if coincurve is None:
        raise RuntimeError("coincurve 不可用，无法签名")
    pk = coincurve.PrivateKey(priv_int.to_bytes(32, "big"))
    # coincurve 的 sign 默认产生可低 S 值的紧凑签名；转 DER
    sig = pk.sign(digest, hasher=None)
    der = sig  # coincurve 返回已是 DER 格式
    return der + bytes([hash_type])


# --------------------------------------------------------------------------
# UTXO 获取
# --------------------------------------------------------------------------
def fetch_utxos(address: str, timeout: int = 20) -> list:
    """从 mempool.space / blockstream 获取未花费输出。"""
    last = None
    for base in C.BTC_APIS:
        try:
            j = C._get_json(f"{base}/address/{address}/utxo", timeout=timeout, retries=2)
            out = []
            for u in j or []:
                if u.get("status", {}).get("confirmed") is False:
                    continue  # 未确认的暂不使用
                out.append({
                    "txid": u["txid"], "vout": u["vout"], "value": u["value"],
                    "confirmed": True,
                })
            return out
        except Exception as exc:
            last = exc
    raise RuntimeError(f"无法获取 UTXO: {last}")


# --------------------------------------------------------------------------
# 构造并签名 sweep 交易
# --------------------------------------------------------------------------
def build_sweep_tx(privkey: str, src_addr: str, dst_addr: str, utxos: list,
                   send_value: int, fee_rate: int = 10, timeout: int = 20) -> str:
    """构造把全部 UTXO 扫到 dst 的交易，返回原始 hex。"""
    priv_int = int(privkey, 16)
    pubkey = _pubkey_compressed(priv_int)

    # 判断地址类型
    is_bech32 = src_addr.startswith("bc1")
    is_p2sh = src_addr.startswith("3")
    if is_bech32:
        prevout_spk = _spk_p2wpkh(pubkey)
    elif is_p2sh:
        prevout_spk = b"\xa9\x14" + _hash160(b"\x00\x14" + _hash160(pubkey)) + b"\x87"
    else:
        prevout_spk = _spk_p2pkh(pubkey)

    # 目标脚本
    if dst_addr.startswith("bc1"):
        witprog = _decode_bech32(dst_addr)
        dst_spk = b"\x00\x14" + witprog
    elif dst_addr.startswith("3"):
        dst_spk = b"\xa9\x14" + base58.b58decode_check(dst_addr)[1:] + b"\x87"
    else:
        dst_spk = b"\x76\xa9\x14" + base58.b58decode_check(dst_addr)[1:] + b"\x88\xac"

    inputs = [(u["txid"], u["vout"], b"", 0xFFFFFFFF) for u in utxos]
    outputs = [(send_value, dst_spk)]

    witnesses = []
    for i, u in enumerate(utxos):
        if is_bech32:
            digest = _bip143_sighash(inputs, outputs, i, u["value"], prevout_spk, pubkey)
        elif is_p2sh:
            digest = _bip143_sighash_p2sh_p2wpkh(inputs, outputs, i, u["value"], pubkey)
        else:
            digest = _legacy_sighash(inputs, outputs, i, prevout_spk)
        sig = _sign(priv_int, digest)
        if is_bech32:
            witnesses.append([sig, pubkey])
        elif is_p2sh:
            redeem = b"\x00\x14" + _hash160(pubkey)
            witnesses.append([sig, pubkey])
        else:
            # legacy：scriptSig 内联签名与公钥
            script_sig = bytes([len(sig)]) + sig + bytes([len(pubkey)]) + pubkey
            inputs[i] = (u["txid"], u["vout"], script_sig, 0xFFFFFFFF)

    if is_p2sh:
        # P2SH-P2WPKH：scriptSig 为 push redeemScript
        redeem = b"\x00\x14" + _hash160(pubkey)
        for i in range(len(inputs)):
            txid, vout, _, seq = inputs[i]
            inputs[i] = (txid, vout, bytes([len(redeem)]) + redeem, seq)

    segwit = is_bech32 or is_p2sh
    raw = _ser_tx(2, inputs, outputs, 0, segwit=segwit,
                  witnesses=witnesses if segwit else None)
    return raw.hex()


def _legacy_sighash(inputs, outputs, index, prevout_spk, hash_type=SIGHASH_ALL) -> bytes:
    """传统（非 segwit）签名哈希。"""
    signed_inputs = []
    for i, (txid, vout, _, seq) in enumerate(inputs):
        signed_inputs.append((txid, vout, prevout_spk if i == index else b"", seq))
    raw = _ser_tx(2, signed_inputs, outputs, 0) + struct.pack("<I", hash_type)
    return hashlib.sha256(hashlib.sha256(raw).digest()).digest()


def _decode_bech32(addr: str) -> bytes:
    """从 bech32 地址解出 witness program。"""
    pos = addr.rfind("1")
    data_part = addr[pos + 1:]
    charset = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    data = [charset.index(c) for c in data_part]
    # 去掉 6 位校验和，去掉版本字节，8->5 反转换
    payload = data[1:-6]
    return bytes(_convertbits(payload, 5, 8, False))
