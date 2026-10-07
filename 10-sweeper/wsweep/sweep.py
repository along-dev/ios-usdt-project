# -*- coding: utf-8 -*-
"""归集（sweep）：把各链余额转到指定目标地址。

复用来源：
  - E:\\CTF-任务\\evccoin\\artifacts\\evccoin\\sim_sweep.py
      ERC20 transfer calldata 构造（a9059cbb + 左填充地址 + 金额）、nonce/gasPrice 读取、
      eth_estimateGas 预估、离线签名不广播的 dry-run 模式

安全设计：
  - 默认 dry_run=True：只构造并签名交易，打印将发生什么，绝不广播。
  - 必须显式传入 broadcast=True 才会真正发送（由 CLI 的 --broadcast 控制）。
  - 每笔转账前检查 native 余额是否足够支付 gas；不足则跳过并记录原因。
  - EVM 归集顺序：先转 ERC20，最后转 native（否则 gas 会被先转走）。
  - 支持 --leave-native-gas 保留少量 native 作为后续 gas。
"""
from __future__ import annotations

import json
import time

try:
    from eth_account import Account
except Exception:  # pragma: no cover
    Account = None

from . import chains as C
from .derive import N

# ERC20 / TRC20 / SPL transfer 相关
SEL_TRANSFER = "0xa9059cbb"
EVM_GAS_LIMIT_ERC20 = 65000
EVM_GAS_LIMIT_NATIVE = 21000
# 归集时保留的最小 native（避免 gas 不足），单位为该链原生币
DEFAULT_LEAVE_NATIVE = {
    "eth": 0.0008, "bsc": 0.0008, "polygon": 0.3, "arbitrum": 0.0002,
    "base": 0.0002, "optimism": 0.0002,
}


class SweepPlan:
    """一次归集计划的条目，便于 dry-run 展示与人工核对。"""

    def __init__(self, chain: str, kind: str, symbol: str, src: str, dst: str,
                 amount: float, raw_amount: int, ok: bool, reason: str = "",
                 tx_hash: str = "", gas_cost: float = 0.0):
        self.chain = chain
        self.kind = kind          # native | erc20 | trc20 | btc | spl
        self.symbol = symbol
        self.src = src
        self.dst = dst
        self.amount = amount
        self.raw_amount = raw_amount
        self.ok = ok
        self.reason = reason
        self.tx_hash = tx_hash
        self.gas_cost = gas_cost

    def to_dict(self):
        return {
            "chain": self.chain, "kind": self.kind, "symbol": self.symbol,
            "from": self.src, "to": self.dst, "amount": self.amount,
            "raw_amount": self.raw_amount, "ok": self.ok, "reason": self.reason,
            "tx_hash": self.tx_hash, "gas_cost": self.gas_cost,
        }


def _erc20_transfer_data(to_addr: str, amount: int) -> str:
    """复用 sim_sweep.py 的构造方式：selector + 32B 地址 + 32B 金额。"""
    return SEL_TRANSFER + to_addr[2:].lower().rjust(64, "0") + format(amount, "064x")


# --------------------------------------------------------------------------
# EVM 归集
# --------------------------------------------------------------------------
def sweep_evm_chain(chain: str, privkey: str, src_addr: str, dst: str,
                    token_filter: list = None, broadcast: bool = False,
                    leave_native: float = None, timeout: int = 30) -> list:
    """归集单条 EVM 链上某地址的全部主流币。"""
    if Account is None:
        return [SweepPlan(chain, "native", "", src_addr, dst, 0, 0, False,
                          "eth_account 不可用，无法签名")]
    cfg = C.EVM_CHAINS[chain]
    rpc_url = cfg["rpc"]
    plans = []

    # --- 读取链上状态 ---
    nonce_res, err = C.rpc_single(rpc_url, "eth_getTransactionCount", [src_addr, "pending"])
    if err or nonce_res is None:
        return [SweepPlan(chain, "native", cfg["symbol"], src_addr, dst, 0, 0, False,
                          f"读取 nonce 失败: {err}")]
    nonce = int(nonce_res, 16)

    gas_price_res, err = C.rpc_single(rpc_url, "eth_gasPrice", [])
    gas_price = int(gas_price_res, 16) if gas_price_res else 5_000_000_000

    bal_res, err = C.rpc_single(rpc_url, "eth_getBalance", [src_addr, "latest"])
    native_wei = int(bal_res, 16) if bal_res else 0

    # --- 先处理 ERC20 ---
    tokens = C.EVM_TOKENS.get(chain, [])
    if token_filter:
        tokens = [t for t in tokens if t[0].upper() in {s.upper() for s in token_filter}]

    eth_used = 0
    for sym, token, dec in tokens:
        data_bal = C.SEL_BALANCE_OF + src_addr[2:].lower().rjust(64, "0")
        res, err = C.rpc_single(rpc_url, "eth_call", [{"to": token, "data": data_bal}, "latest"])
        if err or not res or res == "0x":
            continue
        try:
            raw = int(res, 16)
        except Exception:
            continue
        if raw <= 0:
            continue

        gas_needed = EVM_GAS_LIMIT_ERC20 * gas_price
        if native_wei < gas_needed + eth_used:
            plans.append(SweepPlan(chain, "erc20", sym, src_addr, dst,
                                   raw / 10 ** dec, raw, False,
                                   f"native 不足以支付 gas（需 {gas_needed/1e18:.6f} {cfg['symbol']}）"))
            continue

        amount = raw / 10 ** dec
        tx = {
            "nonce": nonce, "gasPrice": gas_price, "gas": EVM_GAS_LIMIT_ERC20,
            "to": token, "value": 0, "data": _erc20_transfer_data(dst, raw),
            "chainId": cfg["chain_id"],
        }
        try:
            signed = Account.sign_transaction(tx, "0x" + privkey)
            txhash = signed.hash.hex()
            if not txhash.startswith("0x"):
                txhash = "0x" + txhash
        except Exception as exc:
            plans.append(SweepPlan(chain, "erc20", sym, src_addr, dst, amount, raw, False,
                                   f"签名失败: {exc}"))
            continue

        if broadcast:
            sent, serr = C.rpc_single(rpc_url, "eth_sendRawTransaction",
                                      [signed.raw_transaction.hex()
                                       if hasattr(signed, "raw_transaction") else signed.rawTransaction.hex()])
            if serr or not sent:
                plans.append(SweepPlan(chain, "erc20", sym, src_addr, dst, amount, raw, False,
                                       f"广播失败: {serr}"))
                continue
            txhash = sent
            nonce += 1

        eth_used += gas_needed
        plans.append(SweepPlan(chain, "erc20", sym, src_addr, dst, amount, raw, True,
                               "已广播" if broadcast else "dry-run（未广播）",
                               txhash, gas_needed / 1e18))
        if not broadcast:
            nonce += 1

    # --- 再处理 native ---
    leave = DEFAULT_LEAVE_NATIVE.get(chain, 0.0008) if leave_native is None else leave_native
    leave_wei = int(leave * 1e18)
    available = native_wei - eth_used - leave_wei
    gas_native = EVM_GAS_LIMIT_NATIVE * gas_price

    if available <= gas_native:
        plans.append(SweepPlan(chain, "native", cfg["symbol"], src_addr, dst, 0, 0, False,
                               f"原生币不足（余额 {native_wei/1e18:.8f}，"
                               f"预留 {leave}，gas 需 {gas_native/1e18:.8f}）"))
    else:
        send_wei = available - gas_native
        tx = {
            "nonce": nonce, "gasPrice": gas_price, "gas": EVM_GAS_LIMIT_NATIVE,
            "to": dst, "value": send_wei, "data": "0x", "chainId": cfg["chain_id"],
        }
        try:
            signed = Account.sign_transaction(tx, "0x" + privkey)
            txhash = signed.hash.hex()
            if not txhash.startswith("0x"):
                txhash = "0x" + txhash
            if broadcast:
                sent, serr = C.rpc_single(rpc_url, "eth_sendRawTransaction",
                                          [signed.raw_transaction.hex()
                                           if hasattr(signed, "raw_transaction") else signed.rawTransaction.hex()])
                if serr or not sent:
                    plans.append(SweepPlan(chain, "native", cfg["symbol"], src_addr, dst,
                                           send_wei / 1e18, send_wei, False, f"广播失败: {serr}"))
                    return plans
                txhash = sent
            plans.append(SweepPlan(chain, "native", cfg["symbol"], src_addr, dst,
                                   send_wei / 1e18, send_wei, True,
                                   "已广播" if broadcast else "dry-run（未广播）",
                                   txhash, gas_native / 1e18))
        except Exception as exc:
            plans.append(SweepPlan(chain, "native", cfg["symbol"], src_addr, dst,
                                   send_wei / 1e18, send_wei, False, f"签名失败: {exc}"))
    return plans


# --------------------------------------------------------------------------
# TRON 归集
# --------------------------------------------------------------------------
def sweep_tron(privkey: str, src_addr: str, dst: str, broadcast: bool = False,
               timeout: int = 30) -> list:
    """TRON 归集：TRX + TRC20-USDT。

    使用 tron_tx 中手写 protobuf 的实现，不依赖 tronpy。
    """
    plans = []
    try:
        from . import tron_tx
    except Exception as exc:
        plans.append(SweepPlan("tron", "native", "TRX", src_addr, dst, 0, 0, False,
                               f"TRON 交易模块不可用: {exc}"))
        return plans

    try:
        results = tron_tx.sweep_address(src_addr, dst, privkey,
                                        broadcast_it=broadcast, timeout=timeout)
        for kind, symbol, raw, ok, reason, txid in results:
            dec = 6  # TRX 与 USDT 都是 6 位小数
            plans.append(SweepPlan("tron", kind, symbol, src_addr, dst,
                                   raw / 10 ** dec, raw, ok, reason, txid,
                                   gas_cost=0.0))
    except Exception as exc:
        plans.append(SweepPlan("tron", "native", "TRX", src_addr, dst, 0, 0, False,
                               f"{type(exc).__name__}: {exc}"))
    return plans


# --------------------------------------------------------------------------
# BTC 归集
# --------------------------------------------------------------------------
def sweep_btc(privkey: str, src_addr: str, dst: str, broadcast: bool = False,
              fee_rate: int = 10, timeout: int = 30) -> list:
    """BTC 归集：构造 P2WPKH / P2PKH 全部余额转账。

    UTXO 选取与 PSBT 构造较复杂，此处给出可用的最小实现框架；
    真正广播需要精确的脚本签名（BIP143）。
    """
    plans = []
    try:
        from .btc_tx import build_sweep_tx, fetch_utxos
    except Exception as exc:
        plans.append(SweepPlan("btc", "btc", "BTC", src_addr, dst, 0, 0, False,
                               f"BTC 交易模块不可用: {exc}"))
        return plans

    try:
        utxos = fetch_utxos(src_addr)
        total = sum(u["value"] for u in utxos)
        if total <= 0:
            plans.append(SweepPlan("btc", "btc", "BTC", src_addr, dst, 0, 0, False, "无可用 UTXO"))
            return plans
        # 估算手续费：1 输入 ~68 vB，2 输出 ~62 vB
        est_vsize = 11 + 68 * len(utxos) + 62
        fee = est_vsize * fee_rate
        send = total - fee
        if send <= 546:
            plans.append(SweepPlan("btc", "btc", "BTC", src_addr, dst, 0, 0, False,
                                   f"余额不足以覆盖手续费（总 {total} sat，费 {fee} sat）"))
            return plans
        raw_hex = build_sweep_tx(privkey, src_addr, dst, utxos, send, fee_rate)
        if broadcast:
            try:
                j = C._post_json(f"{C.BTC_APIS[0]}/tx", raw_hex, timeout=timeout)
                txid = j if isinstance(j, str) else str(j)
            except Exception:
                # mempool.space 期望纯文本 body
                import urllib.request
                req = urllib.request.Request(f"{C.BTC_APIS[0]}/tx", raw_hex.encode(),
                                             {"Content-Type": "text/plain"}, method="POST")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    txid = resp.read().decode().strip()
            plans.append(SweepPlan("btc", "btc", "BTC", src_addr, dst, send / 1e8, send,
                                   True, "已广播", txid))
        else:
            plans.append(SweepPlan("btc", "btc", "BTC", src_addr, dst, send / 1e8, send,
                                   True, "dry-run（未广播）", raw_hex[:64] + "..."))
    except Exception as exc:
        plans.append(SweepPlan("btc", "btc", "BTC", src_addr, dst, 0, 0, False,
                               f"{type(exc).__name__}: {exc}"))
    return plans


# --------------------------------------------------------------------------
# Solana 归集
# --------------------------------------------------------------------------
def sweep_solana(privkey: str, src_addr: str, dst: str, broadcast: bool = False,
                 timeout: int = 30) -> list:
    """Solana 归集：SOL 原生 + SPL USDT/USDC。

    使用 sol_tx 中手写的 Solana legacy 交易实现（nacl 签名 + 自序列化），
    不依赖 solders / solana-py。
    """
    plans = []
    try:
        from . import sol_tx
    except Exception as exc:
        plans.append(SweepPlan("sol", "native", "SOL", src_addr, dst, 0, 0, False,
                               f"Solana 交易模块不可用: {exc}"))
        return plans

    try:
        results = sol_tx.sweep_address(src_addr, dst, privkey,
                                       broadcast_it=broadcast, timeout=timeout)
        for kind, symbol, raw, ok, reason, sig in results:
            dec = 9 if symbol == "SOL" else 6   # SOL 9 位；USDT/USDC 6 位
            plans.append(SweepPlan("sol", kind, symbol, src_addr, dst,
                                   raw / 10 ** dec, raw, ok, reason, sig))
    except Exception as exc:
        plans.append(SweepPlan("sol", "native", "SOL", src_addr, dst, 0, 0, False,
                               f"{type(exc).__name__}: {exc}"))
    return plans


# --------------------------------------------------------------------------
# 编排
# --------------------------------------------------------------------------
def execute(accounts: list, target_evm: str, target_tron: str = "", target_btc: str = "",
            target_sol: str = "", chains: list = None, tokens: list = None,
            broadcast: bool = False, leave_native: float = None) -> list:
    """对所有派生账户执行归集。

    四个目标地址彼此独立、均为可选：某条链没有提供目标地址时，
    该链整体跳过（不产生计划条目），而不是回退到 EVM 地址 —— 因为
    EVM/TRON/BTC/SOL 的地址格式互斥，混用只会失败。
    """
    chains = chains or ["evm", "tron", "btc", "sol"]
    all_plans = []

    # 规范化：只有非空目标才视为该链启用
    t_evm = (target_evm or "").strip()
    t_tron = (target_tron or "").strip()
    t_btc = (target_btc or "").strip()
    t_sol = (target_sol or "").strip()

    for acc in accounts:
        # --- EVM（6 条链共用同一个 0x 地址）---
        if "evm" in chains and t_evm and acc.evm_address and acc.evm_privkey:
            for cname in C.EVM_CHAINS:
                try:
                    all_plans.extend(sweep_evm_chain(
                        cname, acc.evm_privkey, acc.evm_address, t_evm,
                        token_filter=tokens, broadcast=broadcast, leave_native=leave_native))
                except Exception as exc:
                    all_plans.append(SweepPlan(cname, "native", "", acc.evm_address,
                                               t_evm, 0, 0, False,
                                               f"{type(exc).__name__}: {exc}"))

        # --- TRON（独立 T 地址）---
        if "tron" in chains and t_tron and acc.tron_address and acc.tron_privkey:
            try:
                all_plans.extend(sweep_tron(acc.tron_privkey, acc.tron_address, t_tron,
                                            broadcast=broadcast))
            except Exception as exc:
                all_plans.append(SweepPlan("tron", "native", "", acc.tron_address, t_tron,
                                           0, 0, False, f"{type(exc).__name__}: {exc}"))

        # --- BTC（独立 BTC 地址）---
        if "btc" in chains and t_btc and acc.btc.get("p2wpkh") and acc.btc_privkey:
            try:
                all_plans.extend(sweep_btc(acc.btc_privkey, acc.btc["p2wpkh"], t_btc,
                                           broadcast=broadcast))
            except Exception as exc:
                all_plans.append(SweepPlan("btc", "btc", "", acc.btc["p2wpkh"], t_btc,
                                           0, 0, False, f"{type(exc).__name__}: {exc}"))

        # --- Solana（独立 SOL 地址）---
        if "sol" in chains and t_sol and acc.sol_address and acc.sol_privkey:
            try:
                all_plans.extend(sweep_solana(acc.sol_privkey, acc.sol_address, t_sol,
                                              broadcast=broadcast))
            except Exception as exc:
                all_plans.append(SweepPlan("sol", "native", "", acc.sol_address, t_sol,
                                           0, 0, False, f"{type(exc).__name__}: {exc}"))

    return all_plans
