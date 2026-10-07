# -*- coding: utf-8 -*-
"""账户控制权与 gas 可行性检测。

回答两个关键问题：
  A. gas 够不够？—— 该地址的原生币是否足以支付归集所需手续费
  B. 我们说了算吗？—— 账户是否被多签、权限是否被转移

为什么必须查这两项
------------------------------------------------------------------
  余额非零 ≠ 能拿走。现实中的失败模式：
    · EVM : 合约钱包（Safe/多签）的 EOA owner 无直接转账权
    · TRON: owner_permission / active_permission 被改成别人的地址
            （本项目实测样本 TUEZSdKso… 正是如此，私钥在手也转不走）
    · BTC : 地址类型是 P2SH 多签，或 UTXO 被时间锁
    · SOL : 账户 owner 不是 System Program（而是某个 program 托管）
"""

# --------------------------------------------------------------------------
# EVM
# --------------------------------------------------------------------------
def check_evm(rpc_url: str, address: str, privkey: str) -> dict:
    """检查 EVM 地址的控制权与 gas。

    返回 dict：
      code_size        合约代码长度（>0 表示这是合约，不是普通 EOA）
      is_contract      是否是合约账户
      is_multisig      是否疑似多签/合约钱包
      owner_ok         我们的私钥是否就是控制者
      gas_native       原生币余额（可付 gas）
      gas_ok           余额是否够一笔归集
      note             说明
    """
    out = {
        "is_contract": False, "code_size": 0, "is_multisig": False,
        "owner_ok": True, "gas_native": 0.0, "gas_ok": False, "note": "",
        "is_eip7702": False, "delegate_to": "", "is_eoa": False,
    }
    try:
        from .chains import rpc_single
        # --- 代码长度：判断是否合约 ---
        res, err = rpc_single(rpc_url, "eth_getCode", [address, "latest"])
        if isinstance(res, str) and res not in ("0x", "0x0", ""):
            code = res[2:] if res.startswith("0x") else res
            # EIP-7702 delegation designator: 0xef0100 || 20 字节地址
            if code.startswith("ef0100") and len(code) == 46:
                delegate = "0x" + code[6:46]
                out["is_eip7702"] = True
                out["delegate_to"] = delegate
                out["is_eoa"] = True          # 私钥仍是 EOA，可签名
                out["owner_ok"] = True
                out["note"] = (f"⚠ EIP-7702 委托账户：代码执行被委托给 {delegate}。"
                               f"私钥可签名，但交易会经该合约执行，存在资金被控制风险")
            else:
                out["is_contract"] = True
                out["code_size"] = len(code) // 2
        # --- 原生币余额 ---
        res2, err2 = rpc_single(rpc_url, "eth_getBalance", [address, "latest"])
        if isinstance(res2, str) and res2 != "0x":
            out["gas_native"] = int(res2, 16) / 1e18
        # --- gas 价格 ---
        res3, _ = rpc_single(rpc_url, "eth_gasPrice", [])
        gas_price = int(res3, 16) if res3 else 5_000_000_000

        # 一笔 ERC20 归集约 65000 gas
        need = 65000 * gas_price / 1e18
        out["gas_need"] = need
        out["gas_ok"] = out["gas_native"] > need

        # --- 多签识别（仅真正的合约账户；7702 委托账户单独处理）---
        if out["is_contract"]:
            # Safe(前 Gnosis) 的 getThreshold() selector = 0xe75235b8
            # 以及 getOwners() = 0xa0e67e2b
            thr, _ = rpc_single(rpc_url, "eth_call",
                                [{"to": address, "data": "0xe75235b8"}, "latest"])
            if isinstance(thr, str) and thr not in ("0x", "") and len(thr) >= 66:
                try:
                    threshold = int(thr, 16)
                    if 1 <= threshold <= 50:
                        out["is_multisig"] = True
                        out["multisig_threshold"] = threshold
                        out["note"] = f"疑似多签合约钱包（阈值 {threshold}）"
                except Exception:
                    pass
            if not out["is_multisig"]:
                out["note"] = f"合约账户（代码 {out['code_size']} 字节），私钥无法直接转账"
            out["owner_ok"] = False
        elif out["is_eip7702"]:
            # 7702 委托账户：私钥仍是 EOA，可签名，但执行被委托合约接管
            # 已在上方设置 owner_ok=True 与 note，这里只补充 gas 判断
            pass
        elif out["gas_native"] == 0:
            out["note"] = "普通 EOA，但无原生币支付 gas"
        else:
            out["note"] = "普通 EOA"
    except Exception as exc:
        out["note"] = f"检测失败: {type(exc).__name__}: {exc}"
    return out


# --------------------------------------------------------------------------
# TRON
# --------------------------------------------------------------------------
def check_tron(address: str, privkey: str) -> dict:
    """检查 TRON 账户的权限归属与 gas。

    TRON 的 account 结构里 owner_permission / active_permission 的 keys
    决定了谁能签名。若 owner 被改成别的地址，私钥在手也无效。
    """
    out = {
        "owner_ok": True, "is_multisig": False, "gas_native": 0.0,
        "gas_ok": False, "note": "", "owner_address": "", "active_addresses": [],
    }
    try:
        from . import chains as C
        from .derive import tron_address
        base = C.TRON_RPC[0]
        acct = C._post_json(f"{base}/wallet/getaccount",
                            {"address": address, "visible": True}, timeout=20) or {}
        if not acct:
            out["note"] = "账户未激活（链上无记录）"
            return out

        out["gas_native"] = float(acct.get("balance", 0)) / 1e6

        # --- owner_permission 的 keys ---
        op = acct.get("owner_permission") or {}
        op_keys = [k.get("address") for k in (op.get("keys") or []) if k.get("address")]
        out["owner_address"] = op_keys[0] if op_keys else address
        out["owner_threshold"] = op.get("threshold", 1)

        # --- active_permission ---
        act = acct.get("active_permission") or []
        act_addrs = []
        for a in act:
            for k in (a.get("keys") or []):
                if k.get("address"):
                    act_addrs.append(k["address"])
        out["active_addresses"] = act_addrs

        # --- 我们的地址是否等于 owner ---
        our = address
        if op_keys and op_keys[0] != our:
            out["owner_ok"] = False
            out["note"] = f"owner_permission 已转移至 {op_keys[0]}（私钥无法控制）"

        # --- 多签判定：keys 数量 > 1 或 threshold > 1 ---
        if len(op_keys) > 1 or out["owner_threshold"] > 1:
            out["is_multisig"] = True
            out["note"] = (f"多签账户：owner keys={len(op_keys)}，"
                           f"阈值={out['owner_threshold']}")
        for a in act:
            if len(a.get("keys") or []) > 1 or (a.get("threshold") or 1) > 1:
                out["is_multisig"] = True
                out["note"] = (f"active_permission 多签：keys={len(a.get('keys') or [])}，"
                               f"阈值={a.get('threshold')}")

        # --- gas：TRC20 需约 30 TRX 能量费 ---
        need = 30.0
        out["gas_need"] = need
        out["gas_ok"] = out["gas_native"] >= need
        if not out["note"]:
            out["note"] = ("TRX 充足，可执行 TRC20 归集" if out["gas_ok"]
                           else f"TRX 不足（{out['gas_native']:.2f} < {need}）")
    except Exception as exc:
        out["note"] = f"检测失败: {type(exc).__name__}: {exc}"
    return out


# --------------------------------------------------------------------------
# BTC
# --------------------------------------------------------------------------
def check_btc(address: str) -> dict:
    """检查 BTC 地址类型与 gas（UTXO 可花性）。"""
    out = {
        "is_multisig": False, "gas_ok": False, "gas_native": 0.0,
        "utxo_count": 0, "note": "", "addr_type": "",
    }
    try:
        from . import chains as C
        from .btc_tx import fetch_utxos
        # 地址类型
        if address.startswith("bc1q"):
            out["addr_type"] = "P2WPKH (bech32)"
        elif address.startswith("bc1p"):
            out["addr_type"] = "P2TR (taproot)"
        elif address.startswith("3"):
            out["addr_type"] = "P2SH（可能是多签）"
            out["is_multisig"] = True
        elif address.startswith("1"):
            out["addr_type"] = "P2PKH"
        else:
            out["addr_type"] = "未知"

        utxos = fetch_utxos(address)
        out["utxo_count"] = len(utxos)
        total = sum(u["value"] for u in utxos)
        out["gas_native"] = total / 1e8   # 实际是 BTC 本身
        out["gas_ok"] = total > 546 * 2   # 能覆盖手续费
        out["total_sat"] = total

        if out["is_multisig"]:
            out["note"] = "P2SH 地址，可能是多签；单私钥可能无法花费"
        elif total == 0:
            out["note"] = "无可用 UTXO"
        elif not out["gas_ok"]:
            out["note"] = f"UTXO 总额过小（{total} sat），不足以覆盖手续费"
        else:
            out["note"] = f"{out['utxo_count']} 个 UTXO，可归集"
    except Exception as exc:
        out["note"] = f"检测失败: {type(exc).__name__}: {exc}"
    return out


# --------------------------------------------------------------------------
# Solana
# --------------------------------------------------------------------------
def check_solana(rpc_url: str, address: str, privkey: str) -> dict:
    """检查 Solana 账户 owner（是否被 program 托管）与 gas。"""
    out = {
        "owner_ok": True, "is_multisig": False, "gas_native": 0.0,
        "gas_ok": False, "note": "", "account_owner": "",
    }
    try:
        from . import chains as C, sol_tx
        res, err = C.rpc_single(rpc_url, "getAccountInfo",
                                [address, {"encoding": "base64"}], timeout=25)
        if isinstance(res, dict):
            val = res.get("value")
            if val is None:
                out["note"] = "账户未创建（无 lamports）"
                out["gas_ok"] = False
            else:
                out["gas_native"] = float(val.get("lamports", 0)) / 1e9
                owner = val.get("owner", "")
                out["account_owner"] = owner
                # 非 System Program 托管 = 不是普通钱包
                if owner and owner != sol_tx.SYSTEM_PROGRAM:
                    out["owner_ok"] = False
                    out["is_multisig"] = True
                    out["note"] = f"账户由 {owner[:20]}… 程序托管，私钥无法直接转走 SOL"
                else:
                    out["note"] = "普通系统账户"
        need = 0.000005 + 0.00089  # 手续费 + 租金豁免
        out["gas_need"] = need
        out["gas_ok"] = out["gas_native"] > need
        if out["owner_ok"] and not out["gas_ok"] and out["gas_native"] > 0:
            out["note"] = f"SOL 不足（{out['gas_native']:.9f} < {need}）"
    except Exception as exc:
        out["note"] = f"检测失败: {type(exc).__name__}: {exc}"
    return out


# --------------------------------------------------------------------------
# 统一入口
# --------------------------------------------------------------------------
def check_all(acc, chains: list = None) -> dict:
    """对派生账户做全链控制权与 gas 检测。

    acc 需含 evm_address / tron_address / btc / sol_address。
    内部对各链并发查询（6 条 EVM + TRON + BTC + SOL 共 9 项），
    否则 464 个账户串行会耗时过久。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from . import chains as C
    chains = chains or ["evm", "tron", "btc", "sol"]

    jobs = {}   # key -> callable

    if "evm" in chains and acc.evm_address:
        for cname, cfg in C.EVM_CHAINS.items():
            jobs[f"evm:{cname}"] = (lambda c=cfg: check_evm(c["rpc"], acc.evm_address,
                                                            acc.evm_privkey))
    if "tron" in chains and acc.tron_address:
        jobs["tron"] = lambda: check_tron(acc.tron_address, acc.tron_privkey)
    if "btc" in chains and acc.btc.get("p2wpkh"):
        jobs["btc"] = lambda: check_btc(acc.btc["p2wpkh"])
    if "sol" in chains and acc.sol_address:
        jobs["sol"] = lambda: check_solana(C.SOLANA_RPC[0], acc.sol_address,
                                           acc.sol_privkey)

    result = {}
    evm_part = {}
    with ThreadPoolExecutor(max_workers=min(9, max(1, len(jobs)))) as ex:
        futs = {ex.submit(fn): k for k, fn in jobs.items()}
        for fut in as_completed(futs):
            k = futs[fut]
            try:
                v = fut.result()
            except Exception as exc:
                v = {"note": f"检测失败: {type(exc).__name__}: {exc}"}
            if k.startswith("evm:"):
                evm_part[k.split(":", 1)[1]] = v
            else:
                result[k] = v
    if evm_part:
        result["evm"] = evm_part
    return result
