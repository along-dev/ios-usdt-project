# -*- coding: utf-8 -*-
"""EIP-7702 授权与撤销交易构造（本地签名，绝不广播）。

用途
------------------------------------------------------------------
  撤销委托：把 EOA 的委托目标清空（address = 0x0），
  使该地址恢复为普通 EOA，drainer 代码不再被执行。

规范要点（EIP-7702 / Pectra）
------------------------------------------------------------------
  1. 授权项签名的哈希：
       MAGIC = 0x05
       auth_hash = keccak256(MAGIC || rlp([chain_id, address, nonce]))
     其中 address 为委托目标（撤销时填 0x0000...0000）。

  2. SetCode 交易（type 0x04）字段：
       chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas,
       gas_limit, to, value, data, access_list, authorization_list
     authorization_list 每项为 [chain_id, address, nonce, y_parity, r, s]

  3. 授权项的 nonce 必须等于该 EOA 当前的 nonce（或更大，且按顺序）。

重要限制
------------------------------------------------------------------
  · **撤销交易本身也是一笔交易**。若目标地址已被委托给 drainer，
    该交易依然会被 drainer 代码处理（7702 的固有困境）。
  · 因此本模块只负责"构造 + 签名"，是否广播、用什么路径广播
    （公开池 / Flashbots / 抢跑）必须由调用方明确决定。
  · 本模块默认 dry_run=True。
"""
from __future__ import annotations

import rlp
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak

MAGIC = b"\x05"
ZERO_ADDR = "0x0000000000000000000000000000000000000000"

# 撤销一次委托的 gas 估算（含 12500/授权项的前期成本）
GAS_REVOKE = 60_000


# --------------------------------------------------------------------------
# 授权项签名
# --------------------------------------------------------------------------
def _addr_to_bytes(addr: str) -> bytes:
    a = (addr or "").strip()
    if a.startswith(("0x", "0X")):
        a = a[2:]
    if len(a) != 40:
        raise ValueError(f"地址长度非法: {addr}")
    return bytes.fromhex(a)


def auth_hash(chain_id: int, address: str, nonce: int) -> bytes:
    """EIP-7702 授权项签名哈希。"""
    payload = rlp.encode([chain_id, _addr_to_bytes(address), nonce])
    return keccak(MAGIC + payload)


def sign_authorization(privkey: str, chain_id: int, address: str, nonce: int) -> dict:
    """签名一个授权项，返回 [chain_id, address, nonce, y_parity, r, s]。"""
    h = auth_hash(chain_id, address, nonce)
    pk = privkey[2:] if privkey.startswith(("0x", "0X")) else privkey
    acct = Account.from_key("0x" + pk)
    signed = Account.unsafe_sign_hash(h, private_key="0x" + pk)
    # unsafe_sign_hash 返回 v/r/s；v 为 27/28，需转为 0/1
    y_parity = signed.v - 27 if signed.v >= 27 else signed.v
    return {
        "chain_id": chain_id,
        "address": address,
        "nonce": nonce,
        "y_parity": y_parity,
        "r": signed.r,
        "s": signed.s,
        # 以下为便于人工核对
        "_signer": acct.address,
        "_hash": "0x" + h.hex(),
    }


# --------------------------------------------------------------------------
# SetCode 交易（type 0x04）构造
# --------------------------------------------------------------------------
def build_revoke_tx(privkey: str, chain_id: int, nonce: int,
                    gas_price_wei: int, gas_limit: int = GAS_REVOKE,
                    max_priority_fee_wei: int = None) -> dict:
    """构造一笔"撤销委托"的 type-4 交易（未签名）。

    撤销 = authorization_list 中的 address 设为 0x0。
    """
    auth = sign_authorization(privkey, chain_id, ZERO_ADDR, nonce)
    pk = privkey[2:] if privkey.startswith(("0x", "0X")) else privkey
    sender = Account.from_key("0x" + pk).address

    priority = max_priority_fee_wei if max_priority_fee_wei is not None else gas_price_wei
    tx = {
        "type": 4,                     # 0x04 SetCode
        "chainId": chain_id,
        "nonce": nonce,
        "maxPriorityFeePerGas": priority,
        "maxFeePerGas": gas_price_wei,
        "gas": gas_limit,
        "to": sender,                  # 发给自己即可
        "value": 0,
        "data": b"",
        "accessList": [],
        "authorizationList": [
            [auth["chain_id"], auth["address"], auth["nonce"],
             auth["y_parity"], auth["r"], auth["s"]]
        ],
    }
    return {"tx": tx, "auth": auth, "from": sender}


def sign_revoke_tx(privkey: str, chain_id: int, nonce: int,
                   gas_price_wei: int, gas_limit: int = GAS_REVOKE,
                   max_priority_fee_wei: int = None) -> dict:
    """构造并签名撤销交易（手写 type-4 RLP，不依赖 eth-account 的 7702 支持）。

    背景：eth-account 0.14.0 不认识 authorizationList 字段，
    因此这里按 EIP-7702 规范手工完成：
        signing_hash = keccak(0x04 || rlp([
            chain_id, nonce, max_priority_fee_per_gas, max_fee_per_gas,
            gas_limit, to, value, data, access_list, authorization_list
        ]))
        raw = 0x04 || rlp([...同样字段..., y_parity, r, s])
    """
    try:
        built = build_revoke_tx(privkey, chain_id, nonce, gas_price_wei,
                                gas_limit, max_priority_fee_wei)
        tx = built["tx"]
        a = built["auth"]

        auth_item = [a["chain_id"], _addr_to_bytes(a["address"]), a["nonce"],
                     a["y_parity"], a["r"], a["s"]]

        # --- 待签字段（不含签名）---
        unsigned_fields = [
            tx["chainId"],
            tx["nonce"],
            tx["maxPriorityFeePerGas"],
            tx["maxFeePerGas"],
            tx["gas"],
            _addr_to_bytes(tx["to"]),
            tx["value"],
            tx["data"] if isinstance(tx["data"], bytes) else bytes.fromhex(
                tx["data"][2:] if tx["data"].startswith("0x") else tx["data"]),
            tx["accessList"],
            [auth_item],
        ]

        signing_hash = keccak(b"\x04" + rlp.encode(unsigned_fields))

        pk = privkey[2:] if privkey.startswith(("0x", "0X")) else privkey
        sig = Account.unsafe_sign_hash(signing_hash, private_key="0x" + pk)
        y_parity = sig.v - 27 if sig.v >= 27 else sig.v

        signed_fields = unsigned_fields + [y_parity, sig.r, sig.s]
        raw = b"\x04" + rlp.encode(signed_fields)
        raw_hex = "0x" + raw.hex()

        from eth_utils import keccak as _k
        tx_hash = "0x" + _k(raw).hex()

        return {
            "ok": True,
            "from": built["from"],
            "tx_hash": tx_hash,
            "raw": raw_hex,
            "auth": a,
            "chain_id": chain_id,
            "nonce": nonce,
            "gas": gas_limit,
            "signing_hash": "0x" + signing_hash.hex(),
        }
    except Exception as exc:
        return {"ok": False, "from": "", "error": f"{type(exc).__name__}: {exc}",
                "auth": None}


# --------------------------------------------------------------------------
# 成本估算
# --------------------------------------------------------------------------
def estimate_revoke_cost(gas_price_wei: int, gas_limit: int = GAS_REVOKE) -> float:
    """单条撤销的估算成本（单位：该链原生币）。"""
    return gas_limit * gas_price_wei / 1e18
