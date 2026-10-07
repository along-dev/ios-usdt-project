# -*- coding: utf-8 -*-
"""多链余额查询：EVM 6 链 + TRON + BTC + Solana。

复用来源：
  - E:\\CTF-任务\\mana\\artifacts\\mana\\chain_balance_scan.py
      批量 JSON-RPC（id 回填地址）、ThreadPoolExecutor 并发、3 次重试、公共 RPC 节点清单
  - E:\\CTF-任务\\polarisex\\recon\\onchain_balances.py
      eth_call balanceOf 的 selector 拼接方式、原生币 eth_getBalance

全部为只读查询（eth_call / eth_getBalance / HTTP GET），不涉及任何签名或广播。
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------------------------
# 链与代币定义
# --------------------------------------------------------------------------
EVM_CHAINS = {
    "eth":      {"rpc": "https://ethereum-rpc.publicnode.com",            "chain_id": 1,     "symbol": "ETH",   "decimals": 18},
    "bsc":      {"rpc": "https://bsc-rpc.publicnode.com",                 "chain_id": 56,    "symbol": "BNB",   "decimals": 18},
    "polygon":  {"rpc": "https://polygon-bor-rpc.publicnode.com",         "chain_id": 137,   "symbol": "POL",   "decimals": 18},
    "arbitrum": {"rpc": "https://arbitrum-one-rpc.publicnode.com",        "chain_id": 42161, "symbol": "ETH",   "decimals": 18},
    "base":     {"rpc": "https://base-rpc.publicnode.com",                "chain_id": 8453,  "symbol": "ETH",   "decimals": 18},
    "optimism": {"rpc": "https://optimism-rpc.publicnode.com",            "chain_id": 10,    "symbol": "ETH",   "decimals": 18},
}

# 主流 ERC20 / BEP20（按其所在链列出）
EVM_TOKENS = {
    "eth": [
        ("USDT", "0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
        ("USDC", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
        ("DAI",  "0x6B175474E89094C44Da98b954EedeAC495271d0F", 18),
    ],
    "bsc": [
        ("USDT", "0x55d398326f99059fF775485246999027B3197955", 18),
        ("USDC", "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", 18),
        ("BUSD", "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", 18),
    ],
    "polygon": [
        ("USDT", "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", 6),
        ("USDC", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 6),
    ],
    "arbitrum": [
        ("USDT", "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", 6),
        ("USDC", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", 6),
    ],
    "base": [
        ("USDC", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
    ],
    "optimism": [
        ("USDT", "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58", 6),
        ("USDC", "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", 6),
    ],
}

# 顺序即优先级：把可用性高的节点放前面。
# 2026-09-26 实测：api.trongrid.io 在密集查询后返回 403（限速封禁），
# 而 publicnode / tronstack 稳定可用（0.4–0.7s）。trongrid 降到末位备用。
TRON_RPC = [
    "https://tron-rpc.publicnode.com",
    "https://api.tronstack.io",
    "https://api.trongrid.io",
]
TRON_USDT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

SOLANA_RPC = ["https://api.mainnet-beta.solana.com", "https://solana-rpc.publicnode.com"]
SOLANA_USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
SOLANA_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

BTC_APIS = [
    "https://mempool.space/api",
    "https://blockstream.info/api",
]

# 函数选择器（手工计算，避免额外依赖）
SEL_BALANCE_OF = "0x70a08231"
SEL_DECIMALS = "0x313ce567"


# --------------------------------------------------------------------------
# 通用 HTTP / JSON-RPC
# --------------------------------------------------------------------------
def _post_json(url: str, payload, timeout: int = 20, retries: int = 3):
    last = None
    body = json.dumps(payload).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, body,
                {"Content-Type": "application/json", "User-Agent": "curl/8"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            last = exc
            time.sleep(0.6 * (attempt + 1))
    raise last if last else RuntimeError("request failed")


def _get_json(url: str, timeout: int = 20, retries: int = 3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            last = exc
            time.sleep(0.6 * (attempt + 1))
    raise last if last else RuntimeError("request failed")


def _get_text(url: str, timeout: int = 20, retries: int = 3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as exc:
            last = exc
            time.sleep(0.6 * (attempt + 1))
    raise last if last else RuntimeError("request failed")


def rpc_batch(rpc_url: str, method: str, params_list: list, timeout: int = 25):
    """批量 JSON-RPC：一次 HTTP 请求携带多个调用，用 id 回填结果。

    复用 chain_balance_scan.py 的 batch + id 映射模式，显著减少请求数。
    """
    payload = [
        {"jsonrpc": "2.0", "id": i, "method": method, "params": p}
        for i, p in enumerate(params_list)
    ]
    try:
        out = _post_json(rpc_url, payload, timeout=timeout)
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    if not isinstance(out, list):
        return {}, "非预期响应（不是数组）"
    result = {}
    for item in out:
        if isinstance(item, dict) and item.get("id") is not None:
            result[item["id"]] = item.get("result")
    return result, None


def rpc_single(rpc_url: str, method: str, params: list, timeout: int = 20):
    try:
        out = _post_json(rpc_url, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                         timeout=timeout)
        return out.get("result"), out.get("error")
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------
# EVM
# --------------------------------------------------------------------------
def _wei_to_unit(value_hex, decimals: int):
    if not value_hex or value_hex in ("0x", "0x0"):
        return 0.0
    try:
        return int(value_hex, 16) / (10 ** decimals)
    except Exception:
        return 0.0


def evm_balances(chain: str, addresses: list, batch: int = 40, timeout: int = 30) -> dict:
    """查询一批 EVM 地址的原生币 + 主流 ERC20 余额。

    返回 {address_lower: {"native": float, "tokens": {sym: float}}}
    """
    cfg = EVM_CHAINS[chain]
    rpc_url = cfg["rpc"]
    addrs = [a.lower() for a in addresses]
    out = {a: {"native": 0.0, "tokens": {}} for a in addrs}
    errors = []

    # --- 原生币（批量 eth_getBalance） ---
    for start in range(0, len(addrs), batch):
        chunk = addrs[start:start + batch]
        res, err = rpc_batch(rpc_url, "eth_getBalance",
                             [[a, "latest"] for a in chunk], timeout=timeout)
        if err:
            errors.append(f"{chain} native batch@{start}: {err}")
            continue
        for i, a in enumerate(chunk):
            out[a]["native"] = _wei_to_unit(res.get(i), cfg["decimals"])

    # --- ERC20（批量 eth_call） ---
    for sym, token, dec in EVM_TOKENS.get(chain, []):
        for start in range(0, len(addrs), batch):
            chunk = addrs[start:start + batch]
            calls = [[{"to": token, "data": SEL_BALANCE_OF + a[2:].rjust(64, "0")}, "latest"]
                     for a in chunk]
            res, err = rpc_batch(rpc_url, "eth_call", calls, timeout=timeout)
            if err:
                errors.append(f"{chain} {sym} batch@{start}: {err}")
                continue
            for i, a in enumerate(chunk):
                val = _wei_to_unit(res.get(i), dec)
                if val > 0:
                    out[a]["tokens"][sym] = val

    return {"balances": out, "errors": errors}


def evm_chain_id(chain: str):
    cfg = EVM_CHAINS[chain]
    res, err = rpc_single(cfg["rpc"], "eth_chainId", [])
    return res, err


# --------------------------------------------------------------------------
# TRON
# --------------------------------------------------------------------------
def tron_balances(addresses: list, timeout: int = 25) -> dict:
    """TRON：TRX 原生余额 + TRC20-USDT。"""
    out = {a: {"native": 0.0, "tokens": {}} for a in addresses}
    errors = []
    for base in TRON_RPC:
        try:
            # 逐个查询（TronGrid 的账户接口不支持批量）
            okany = False
            for a in addresses:
                try:
                    j = _get_json(f"{base}/v1/accounts/{a}", timeout=timeout, retries=2)
                    data = (j or {}).get("data") or []
                    if data:
                        out[a]["native"] = float(data[0].get("balance", 0)) / 1e6
                        for trc in data[0].get("trc20", []) or []:
                            amt = trc.get(TRON_USDT)
                            if amt:
                                out[a]["tokens"]["USDT"] = float(amt) / 1e6
                    okany = True
                except Exception as exc:
                    errors.append(f"tron {a[:8]}: {type(exc).__name__}")
            if okany:
                return {"balances": out, "errors": errors}
        except Exception as exc:
            errors.append(f"tron endpoint {base}: {type(exc).__name__}")
    return {"balances": out, "errors": errors}


# --------------------------------------------------------------------------
# BTC
# --------------------------------------------------------------------------
def btc_balances(addresses: list, timeout: int = 20, workers: int = 16) -> dict:
    """BTC：通过 mempool.space / blockstream 读取已确认 + 未确认余额。

    单地址查询约 7s（mempool.space 对未缓存地址较慢），因此必须并发；
    串行查 900+ 地址会耗时 2 小时以上。
    """
    out = {a: {"native": 0.0, "tokens": {}} for a in addresses}
    errors = []

    def fetch_one(base, a):
        j = _get_json(f"{base}/address/{a}", timeout=timeout, retries=1)
        cs = (j or {}).get("chain_stats") or {}
        ms = (j or {}).get("mempool_stats") or {}
        funded = cs.get("funded_txo_sum", 0)
        spent = cs.get("spent_txo_sum", 0)
        unconf = ms.get("funded_txo_sum", 0) - ms.get("spent_txo_sum", 0)
        return (funded - spent + unconf) / 1e8

    for base in BTC_APIS:
        try:
            okany = False
            with ThreadPoolExecutor(max_workers=min(workers, max(1, len(addresses)))) as ex:
                futs = {ex.submit(fetch_one, base, a): a for a in addresses}
                for fut in as_completed(futs):
                    a = futs[fut]
                    try:
                        out[a]["native"] = fut.result()
                        okany = True
                    except Exception as exc:
                        errors.append(f"btc {a[:10]}: {type(exc).__name__}")
            if okany:
                return {"balances": out, "errors": errors}
        except Exception as exc:
            errors.append(f"btc endpoint {base}: {type(exc).__name__}")
    return {"balances": out, "errors": errors}


# --------------------------------------------------------------------------
# Solana
# --------------------------------------------------------------------------
def solana_balances(addresses: list, timeout: int = 25) -> dict:
    """Solana：SOL 原生余额 + SPL USDT/USDC。"""
    out = {a: {"native": 0.0, "tokens": {}} for a in addresses}
    errors = []
    for rpc_url in SOLANA_RPC:
        try:
            okany = False
            # 原生 SOL
            for a in addresses:
                try:
                    res, err = rpc_single(rpc_url, "getBalance", [a], timeout=timeout)
                    if isinstance(res, dict):
                        out[a]["native"] = res.get("value", 0) / 1e9
                        okany = True
                    elif err:
                        errors.append(f"sol {a[:8]}: {str(err)[:60]}")
                except Exception as exc:
                    errors.append(f"sol {a[:8]}: {type(exc).__name__}")

            # SPL 代币
            for mint, sym in ((SOLANA_USDT, "USDT"), (SOLANA_USDC, "USDC")):
                for a in addresses:
                    try:
                        res, err = rpc_single(
                            rpc_url, "getTokenAccountsByOwner",
                            [a, {"mint": mint}, {"encoding": "jsonParsed"}], timeout=timeout)
                        if isinstance(res, dict):
                            tot = 0.0
                            for acc in res.get("value", []) or []:
                                try:
                                    info = acc["account"]["data"]["parsed"]["info"]
                                    tot += float(info["tokenAmount"]["uiAmount"] or 0)
                                except Exception:
                                    pass
                            if tot > 0:
                                out[a]["tokens"][sym] = tot
                    except Exception as exc:
                        errors.append(f"sol {sym} {a[:8]}: {type(exc).__name__}")
            if okany:
                return {"balances": out, "errors": errors}
        except Exception as exc:
            errors.append(f"sol endpoint {rpc_url}: {type(exc).__name__}")
    return {"balances": out, "errors": errors}


# --------------------------------------------------------------------------
# 统一编排
# --------------------------------------------------------------------------
def collect_addresses(accounts: list) -> dict:
    """把派生账户列表归拢成"每链一批地址"。"""
    buckets = {
        "evm": {},
        "tron": {},
        "btc": {},
        "sol": {},
    }
    for acc in accounts:
        if acc.evm_address:
            buckets["evm"][acc.evm_address.lower()] = acc
        if acc.tron_address:
            buckets["tron"][acc.tron_address] = acc
        if acc.btc.get("p2wpkh"):
            buckets["btc"][acc.btc["p2wpkh"]] = acc
        if acc.btc.get("p2pkh"):
            buckets["btc"][acc.btc["p2pkh"]] = acc
        if acc.sol_address:
            buckets["sol"][acc.sol_address] = acc
    return buckets


def scan_all(accounts: list, chains: list = None, workers: int = 6, verbose: bool = True) -> dict:
    """并发查询所有链的余额，返回结构化结果。

    chains 可选值: evm, tron, btc, sol（evm 会展开为 6 条 EVM 链）
    """
    chains = chains or ["evm", "tron", "btc", "sol"]
    buckets = collect_addresses(accounts)
    results = {}
    errors = []

    tasks = []  # (key, callable)
    if "evm" in chains:
        for cname in EVM_CHAINS:
            addrs = list(buckets["evm"].keys())
            if addrs:
                tasks.append((f"evm:{cname}", lambda c=cname, a=addrs: evm_balances(c, a)))
    if "tron" in chains and buckets["tron"]:
        tasks.append(("tron", lambda a=list(buckets["tron"].keys()): tron_balances(a)))
    if "btc" in chains and buckets["btc"]:
        tasks.append(("btc", lambda a=list(buckets["btc"].keys()): btc_balances(a)))
    if "sol" in chains and buckets["sol"]:
        tasks.append(("sol", lambda a=list(buckets["sol"].keys()): solana_balances(a)))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn): key for key, fn in tasks}
        for fut in as_completed(futs):
            key = futs[fut]
            try:
                r = fut.result()
                results[key] = r.get("balances", {})
                errors.extend(r.get("errors", []))
                if verbose:
                    funded = sum(
                        1 for v in results[key].values()
                        if v.get("native", 0) > 0 or v.get("tokens")
                    )
                    print(f"  [完成] {key:14s} 有余额地址 = {funded}", flush=True)
            except Exception as exc:
                errors.append(f"{key}: {type(exc).__name__}: {exc}")
                if verbose:
                    print(f"  [失败] {key}: {type(exc).__name__}", flush=True)

    return {"results": results, "errors": errors, "buckets": buckets}
