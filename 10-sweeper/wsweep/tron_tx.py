# -*- coding: utf-8 -*-
"""TRON 交易构造与签名（不依赖 tronpy）。

TRON 的 Transaction 是 protobuf 编码的，但字段结构简单，可以手工编码，
避免引入 tronpy（其 API 变动频繁且会拉入大量依赖）。

参考：
  - TransferContract   : field 1 (owner_address) / field 2 (to_address) / field 3 (amount)
  - TriggerSmartContract: field 1 (owner) / field 2 (contract) / field 3 (call_value) / field 4 (data)
  - Transaction.raw     : field 1 (ref_block_bytes) / field 4 (ref_block_hash) /
                          field 8 (expiration) / field 11 (contract) / field 14 (timestamp)
  - Transaction         : field 1 (raw_data) / field 2 (signature)

签名：sha256(txID) 的 ECDSA secp256k1 签名（txID = sha256(raw_data)）。
"""
from __future__ import annotations

import hashlib
import struct
import time

from .derive import _keccak256  # noqa: F401  (用于地址校验)
from . import chains as C

try:
    import coincurve
except Exception:  # pragma: no cover
    coincurve = None

# 合约类型常量
CONTRACT_TRANSFER = "TransferContract"
CONTRACT_TRIGGER = "TriggerSmartContract"

USDT_DECIMALS = 6
TRX_DECIMALS = 6
MIN_TRX_FOR_TRC20 = 30_000_000   # 30 TRX，能量+带宽费用经验值
KEEP_TRX = 1_100_000             # 保留 1.1 TRX 便于失败重试


# --------------------------------------------------------------------------
# 最小 protobuf 编码器
# --------------------------------------------------------------------------
def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _tag(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _pb_bytes(field: int, data: bytes) -> bytes:
    return _tag(field, 2) + _varint(len(data)) + data


def _pb_varint(field: int, value: int) -> bytes:
    return _tag(field, 0) + _varint(value)


def _pb_int64(field: int, value: int) -> bytes:
    return _tag(field, 0) + _varint(value & 0xFFFFFFFFFFFFFFFF)


# --------------------------------------------------------------------------
# 地址转换
# --------------------------------------------------------------------------
def addr_to_hex(addr_base58: str) -> bytes:
    """Base58 地址 -> 21 字节原始地址（0x41 前缀）。

    注意：TronGrid 的 legacy /wallet/* 接口只接受 Base58 地址。
    若传入 EVM 0x 地址（四链共用目标地址的常见情形），直接拒绝并给出可读原因，
    避免 Base58 解码抛出难懂的 "Invalid character"。
    """
    import base58
    s = (addr_base58 or "").strip()
    if not s:
        raise ValueError("TRON 地址为空")
    if s.startswith(("0x", "0X")):
        h = s[2:]
        if len(h) == 40 and all(c in "0123456789abcdefABCDEF" for c in h):
            raise ValueError(
                "目标是 EVM(0x) 地址，不是 TRON 地址。TRON 链需要独立的 T 开头地址，"
                "请用 --target-tron 指定，或在报告中排除 tron 链")
        raise ValueError(f"TRON 地址格式非法: {s[:20]}")
    if not s.startswith("T"):
        raise ValueError(f"TRON 地址必须以 T 开头: {s[:20]}")
    if len(s) != 34:
        raise ValueError(f"TRON 地址长度应为 34，实际 {len(s)}: {s[:20]}")
    try:
        raw = base58.b58decode_check(s)
    except ValueError as exc:
        raise ValueError(f"TRON 地址 Base58 校验失败: {s[:20]} ({exc})") from exc
    if len(raw) != 21:
        raise ValueError(f"TRON 地址长度非法: {len(raw)}")
    if raw[0] != 0x41:
        raise ValueError(f"TRON 地址前缀应为 0x41，实际 0x{raw[0]:02x}")
    return raw


# --------------------------------------------------------------------------
# 合约构造
# --------------------------------------------------------------------------
def _contract_transfer(owner: bytes, to: bytes, amount: int) -> bytes:
    """TransferContract（TRX 转账）。"""
    param = _pb_bytes(1, owner) + _pb_bytes(2, to) + _pb_int64(3, amount)
    # Contract.type = TransferContract(1)；parameter.value 为上述 param
    contract = _pb_varint(1, 1) + _pb_bytes(2, _pb_bytes(1, param))
    return contract


def _contract_trigger(owner: bytes, contract: bytes, data: bytes, call_value: int = 0) -> bytes:
    """TriggerSmartContract（TRC20 调用）。"""
    param = (_pb_bytes(1, owner) + _pb_bytes(2, contract)
             + _pb_int64(3, call_value) + _pb_bytes(4, data))
    # Contract.type = TriggerSmartContract(31)
    contract = _pb_varint(1, 31) + _pb_bytes(2, _pb_bytes(1, param))
    return contract


def _raw_data(contracts: list, ref_block_bytes: bytes, ref_block_hash: bytes,
              expiration: int, timestamp: int, fee_limit: int = 0) -> bytes:
    raw = _pb_bytes(1, ref_block_bytes)
    raw += _pb_bytes(4, ref_block_hash)
    for c in contracts:
        raw += _pb_bytes(11, c)
    if fee_limit:
        raw += _pb_int64(18, fee_limit)
    raw += _pb_int64(8, expiration)
    raw += _pb_int64(14, timestamp)
    return raw


def _sign_raw(raw: bytes, privkey_hex: str) -> tuple:
    """签名 raw_data，返回 (txID_hex, signature_hex)。"""
    if coincurve is None:
        raise RuntimeError("coincurve 不可用，无法签名 TRON 交易")
    txid = hashlib.sha256(raw).digest()
    pk = coincurve.PrivateKey(bytes.fromhex(privkey_hex))
    sig = pk.sign_recoverable(txid, hasher=None)
    return txid.hex(), sig.hex()


def build_signed_tx(contracts: list, ref_block: dict, privkey_hex: str,
                    fee_limit: int = 0) -> dict:
    """构造并签名完整交易，返回可提交的 JSON。"""
    now = int(time.time() * 1000)
    ref_bytes = bytes.fromhex(ref_block["ref_block_bytes"])
    ref_hash = bytes.fromhex(ref_block["ref_block_hash"])
    raw = _raw_data(contracts, ref_bytes, ref_hash,
                    now + 60_000, now, fee_limit)
    txid_hex, sig_hex = _sign_raw(raw, privkey_hex)
    return {
        "txID": txid_hex,
        "raw_data": _raw_data_b64(raw),
        "raw_data_hex": raw.hex(),
        "signature": [sig_hex],
        "visible": False,
    }


def _raw_data_b64(raw: bytes) -> str:
    import base64
    return base64.b64encode(raw).decode()


# --------------------------------------------------------------------------
# 节点交互
# --------------------------------------------------------------------------
def get_now_block(rpc_base: str = None, timeout: int = 20) -> dict:
    """获取最新区块，用于填充 ref_block_bytes / ref_block_hash。"""
    bases = [rpc_base] if rpc_base else C.TRON_RPC
    last = None
    for base in bases:
        try:
            j = C._post_json(f"{base}/wallet/getnowblock", {}, timeout=timeout)
            block = j.get("block_header", {}).get("raw_data", {})
            num = block.get("number")
            if num is None:
                raise RuntimeError("响应缺少 number")
            return {
                "ref_block_bytes": f"{num & 0xFFFF:04x}",
                "ref_block_hash": block.get("txTrieRoot", "")[:16],
                "number": num,
            }
        except Exception as exc:
            last = exc
    raise RuntimeError(f"无法获取 TRON 最新区块: {last}")


def get_account(rpc_base: str, addr: str, timeout: int = 20) -> dict:
    for base in ([rpc_base] if rpc_base else C.TRON_RPC):
        try:
            j = C._post_json(f"{base}/wallet/getaccount",
                             {"address": addr, "visible": True}, timeout=timeout)
            return j or {}
        except Exception:
            continue
    return {}


def get_contract_balance(rpc_base: str, owner: str, contract: str, timeout: int = 20) -> int:
    """读 TRC20 balanceOf（用 triggerconstantcontract）。

    注意：parameter 必须是 32 字节地址的 hex（不含 0x），
    owner_address 的 41 前缀要去掉再左填 0 到 64 位。
    """
    owner_raw = addr_to_hex(owner)              # 21 字节，首字节 0x41
    param_hex = owner_raw[1:].hex().rjust(64, "0")
    for base in ([rpc_base] if rpc_base else C.TRON_RPC):
        try:
            j = C._post_json(f"{base}/wallet/triggerconstantcontract", {
                "owner_address": owner,
                "contract_address": contract,
                "function_selector": "balanceOf(address)",
                "parameter": param_hex,
                "visible": True,
            }, timeout=timeout)
            const = (j or {}).get("constant_result") or []
            if const:
                return int(const[0], 16)
        except Exception:
            continue
    return 0


def broadcast(rpc_base: str, tx: dict, timeout: int = 25) -> tuple:
    """广播交易，返回 (成功?, 说明)。"""
    for base in ([rpc_base] if rpc_base else C.TRON_RPC):
        try:
            j = C._post_json(f"{base}/wallet/broadcasttransaction", tx, timeout=timeout)
            if j.get("result") is True:
                return True, tx.get("txID", "")
            code = j.get("code", "")
            msg = j.get("message", "")
            if isinstance(msg, str):
                try:
                    import base64
                    msg = base64.b64decode(msg).decode("utf-8", "replace")
                except Exception:
                    pass
            return False, f"{code} {msg}".strip()
        except Exception as exc:
            last = exc
    return False, f"广播异常: {last}"


# --------------------------------------------------------------------------
# 高层：归集单个 TRON 地址
# --------------------------------------------------------------------------
def build_trc20_transfer_data(to_addr: str, amount: int) -> bytes:
    """构造 TRC20 transfer(address,uint256) 的 calldata。"""
    to_raw = addr_to_hex(to_addr)               # 21 字节
    param_hex = to_raw[1:].hex().rjust(64, "0")  # 去掉 41 前缀，左填到 32 字节
    data_hex = "a9059cbb" + param_hex + format(amount, "064x")
    return bytes.fromhex(data_hex)


def sweep_address(src: str, dst: str, privkey_hex: str, broadcast_it: bool = False,
                  rpc_base: str = None, timeout: int = 25) -> list:
    """归集单个 TRON 地址的 TRX + USDT。

    返回 [(kind, symbol, amount_raw, ok, reason, txid)]，由调用方包装成 SweepPlan。
    """
    out = []
    base = (rpc_base or C.TRON_RPC[0])

    acct = get_account(base, src, timeout=timeout)
    trx_balance = int(acct.get("balance", 0))
    usdt_balance = 0
    try:
        usdt_balance = get_contract_balance(base, src, C.TRON_USDT, timeout=timeout)
    except Exception:
        pass

    if trx_balance <= 0 and usdt_balance <= 0:
        return [("native", "TRX", 0, False, "账户无 TRX 也无 USDT", ""),
                ("trc20", "USDT", 0, False, "账户无 TRX 也无 USDT", "")]

    try:
        ref = get_now_block(base, timeout=timeout)
    except Exception as exc:
        return [("native", "TRX", 0, False, f"获取区块失败: {exc}", ""),
                ("trc20", "USDT", 0, False, f"获取区块失败: {exc}", "")]

    # --- 目标地址必须能被解析；失败则整条 TRON 链给出可读原因 ---
    try:
        dst_raw = addr_to_hex(dst)
    except ValueError as exc:
        return [("native", "TRX", 0, False, f"目标地址不可用: {exc}", ""),
                ("trc20", "USDT", 0, False, f"目标地址不可用: {exc}", "")]

    try:
        src_raw = addr_to_hex(src)
    except ValueError as exc:
        return [("native", "TRX", 0, False, f"源地址不可用: {exc}", ""),
                ("trc20", "USDT", 0, False, f"源地址不可用: {exc}", "")]

    # --- 多签/权限检查：签名有效 ≠ 链上接受 ---
    # TRC20 transfer 走 active_permission；TRX 转账走 owner_permission。
    # 若阈值 > 我们单个 key 的权重，链上将因 weight 不足而拒绝（SIGERROR）。
    perm = check_permissions(acct, src)
    trc20_blocked = None
    native_blocked = None
    if perm["active_threshold"] > perm["our_active_weight"]:
        trc20_blocked = (f"多签账户：active_permission 阈值 "
                         f"{perm['active_threshold']}，我们仅持 weight "
                         f"{perm['our_active_weight']}（需多方共同签名）")
    if perm["owner_threshold"] > perm["our_owner_weight"]:
        native_blocked = (f"多签账户：owner_permission 阈值 "
                          f"{perm['owner_threshold']}，我们仅持 weight "
                          f"{perm['our_owner_weight']}（需多方共同签名）")

    # --- TRC20 优先（先转代币，避免 TRX 用尽导致支付不了能量） ---
    if usdt_balance > 0:
        if trc20_blocked:
            out.append(("trc20", "USDT", usdt_balance, False, trc20_blocked, ""))
        elif trx_balance < MIN_TRX_FOR_TRC20:
            out.append(("trc20", "USDT", usdt_balance, False,
                        f"TRX 不足（{trx_balance/1e6:.2f} < {MIN_TRX_FOR_TRC20/1e6:.0f}）；"
                        f"TRC20 转账需能量/带宽", ""))
        else:
            data = build_trc20_transfer_data(dst, usdt_balance)
            contract = _contract_trigger(src_raw, addr_to_hex(C.TRON_USDT), data)
            tx = build_signed_tx([contract], ref, privkey_hex, fee_limit=100_000_000)
            if broadcast_it:
                ok, info = broadcast(base, tx, timeout=timeout)
                out.append(("trc20", "USDT", usdt_balance, ok,
                            "已广播" if ok else f"广播失败: {info}",
                            info if ok else ""))
            else:
                out.append(("trc20", "USDT", usdt_balance, True,
                            "dry-run（已签名，未广播）", tx["txID"]))
    else:
        out.append(("trc20", "USDT", 0, False, "USDT 余额为 0", ""))

    # --- TRX ---
    send_trx = trx_balance - KEEP_TRX
    if native_blocked:
        out.append(("native", "TRX", send_trx if send_trx > 0 else 0,
                    False, native_blocked, ""))
    elif send_trx <= 0:
        out.append(("native", "TRX", 0, False,
                    f"TRX 余额不足以支付手续费（余额 {trx_balance/1e6:.6f}，"
                    f"保留 {KEEP_TRX/1e6:.1f}）", ""))
    else:
        contract = _contract_transfer(src_raw, dst_raw, send_trx)
        tx = build_signed_tx([contract], ref, privkey_hex, fee_limit=0)
        if broadcast_it:
            ok, info = broadcast(base, tx, timeout=timeout)
            out.append(("native", "TRX", send_trx, ok,
                        "已广播" if ok else f"广播失败: {info}",
                        info if ok else ""))
        else:
            out.append(("native", "TRX", send_trx, True,
                        "dry-run（已签名，未广播）", tx["txID"]))
    return out


def check_permissions(acct: dict, our_addr: str) -> dict:
    """解析账户权限，返回阈值与"我们的权重"。

    TRON 中：
      · owner_permission   —— 账户所有权（改权限、转 TRX 用）
      · active_permission  —— 日常操作（TRC20 transfer 用）
    多签账户若阈值 > 我们单 key 的权重，链上会以 SIGERROR 拒绝。
    """
    out = {
        "owner_threshold": 1, "our_owner_weight": 0,
        "active_threshold": 1, "our_active_weight": 0,
        "owner_keys": 0, "is_multisig": False,
    }
    op = acct.get("owner_permission") or {}
    if op:
        out["owner_threshold"] = int(op.get("threshold") or 1)
        keys = op.get("keys") or []
        out["owner_keys"] = len(keys)
        for k in keys:
            if k.get("address") == our_addr:
                out["our_owner_weight"] = int(k.get("weight") or 0)
    else:
        # 未显式设置 owner_permission 时，默认单签、权重 1
        out["our_owner_weight"] = 1

    aps = acct.get("active_permission") or []
    if aps:
        # 取第一个 active 权限（标准账户只有一个）
        ap = aps[0]
        out["active_threshold"] = int(ap.get("threshold") or 1)
        for k in (ap.get("keys") or []):
            if k.get("address") == our_addr:
                out["our_active_weight"] = int(k.get("weight") or 0)
    else:
        out["our_active_weight"] = out["our_owner_weight"]

    out["is_multisig"] = (out["owner_threshold"] > 1
                          or out["active_threshold"] > 1
                          or out["owner_keys"] > 1)
    return out
