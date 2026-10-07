# -*- coding: utf-8 -*-
"""深挖 C_无gas 类：算清每个地址缺多少 gas、持有什么资产、按项目分组、排优先级。

要点：
  · C_无gas 的 263 个是 SOL —— 需要 SOL 作 gas，资产在 SPL 代币里
  · 因此必须查 SPL 余额（USDT/USDC）才能算价值
  · TRON 7 个、BSC 9 个同理（TRC20 / BEP20）
"""
import sys, os, json, time, collections
sys.path.insert(0, r"E:\ios漏洞\wallet-sweeper")
from concurrent.futures import ThreadPoolExecutor, as_completed
from wsweep import chains as C, tron_tx, sol_tx

BASE = r"E:\ios漏洞\wallet-sweeper"
WORK = os.path.join(BASE, "kv_work")
OUT = os.path.join(BASE, "kv_out")

rows = json.load(open(os.path.join(WORK, "classify.json"), encoding="utf-8"))
pk_map = json.load(open(os.path.join(WORK, "pk_map.json"), encoding="utf-8"))

# 地址 -> 来源 / unit
addr2src = {}
addr2unit = {}
import re
for pk, info in pk_map.items():
    src = info.get("source", "")
    m = re.search(r"[\\/](?:CTF-任务|CTF任务)[\\/]([^\\/]+)", src)
    unit = m.group(1) if m else "(未知)"
    for ch, a in (info.get("addresses") or {}).items():
        if not a:
            continue
        k = a.lower() if ch in ("eth", "bsc") else a
        addr2src[k] = src
        addr2unit[k] = unit

cng = [r for r in rows if r["category"] == "C_无gas"]
print(f"C_无gas 共 {len(cng)}")
print("按链:", dict(collections.Counter(r["chain"] for r in cng)))
print()

# ---------- 补查资产 ----------
t0 = time.time()


def probe_sol(r):
    """查 SOL 账户的 SPL 代币余额（USDT/USDC）+ SOL 余额。"""
    a = r["address"]
    mints = [(C.SOLANA_USDT, "USDT"), (C.SOLANA_USDC, "USDC")]
    out = {"spl": {}}
    for mint, sym in mints:
        for base in C.SOLANA_RPC:
            try:
                accts = sol_tx.get_token_accounts(base, a, mint, timeout=20)
                tot = sum(x.get("ui", 0) for x in accts)
                if tot > 0:
                    out["spl"][sym] = tot
                break
            except Exception:
                continue
    return r, out


def probe_tron(r):
    a = r["address"]
    out = {"spl": {}}
    for base in C.TRON_RPC:
        try:
            u = tron_tx.get_contract_balance(base, a, C.TRON_USDT) / 1e6
            if u > 0:
                out["spl"]["USDT"] = u
            break
        except Exception:
            continue
    return r, out


def probe_evm(r):
    """查 BSC 地址的 BEP20 余额。"""
    a = r["address"]
    out = {"spl": {}}
    toks = C.EVM_TOKENS.get(r["chain"], [])
    for sym, token, dec in toks:
        data = C.SEL_BALANCE_OF + a[2:].lower().rjust(64, "0")
        for _ in range(2):
            try:
                res, err = C.rpc_single(C.EVM_CHAINS[r["chain"]]["rpc"], "eth_call",
                                        [{"to": token, "data": data}, "latest"], timeout=20)
                if res and res != "0x":
                    v = int(res, 16) / 10 ** dec
                    if v > 0:
                        out["spl"][sym] = v
                break
            except Exception:
                continue
    return r, out


print("补查 C_无gas 的资产（SPL / TRC20 / BEP20）…")
futs = []
with ThreadPoolExecutor(max_workers=16) as ex:
    for r in cng:
        if r["chain"] == "sol":
            futs.append(ex.submit(probe_sol, r))
        elif r["chain"] == "tron":
            futs.append(ex.submit(probe_tron, r))
        else:
            futs.append(ex.submit(probe_evm, r))
    done = 0
    for f in as_completed(futs):
        try:
            r, extra = f.result()
            r["tokens"] = extra.get("spl", {})
        except Exception:
            pass
        done += 1
        if done % 50 == 0:
            print(f"  {done}/{len(cng)}  [{time.time()-t0:.0f}s]", flush=True)

# ---------- 补 unit ----------
for r in cng:
    k = r["address"].lower() if r["chain"] in ("eth", "bsc") else r["address"]
    r["unit"] = addr2unit.get(k, "(未知)")
    r["source"] = addr2src.get(k, "")

# ---------- 计算缺口 ----------
GAS_NEED = {"sol": 0.000895, "tron": 30.0, "bsc": 0.0002, "eth": 0.0008,
            "polygon": 0.3, "btc": 0.00001}

for r in cng:
    need = GAS_NEED.get(r["chain"], 0.001)
    have = r.get("gas_native") or 0
    r["gas_need"] = need
    r["gas_gap"] = max(0.0, need - have)

# ---------- 排序：有代币资产 > 缺 gas 少 ----------
def score(r):
    toks = r.get("tokens") or {}
    tot = sum(toks.values())
    return (1 if toks else 0, tot, -r.get("gas_gap", 9))

cng.sort(key=score, reverse=True)

with_tok = [r for r in cng if r.get("tokens")]
print(f"\n=== 持有代币的 C_无gas：{len(with_tok)} / {len(cng)} ===")
bad = collections.Counter()
for r in with_tok:
    for s in r["tokens"]:
        bad[s] += 1
print(f"  按代币: {dict(bad)}")

out = {
    "total": len(cng),
    "with_tokens": len(with_tok),
    "items": cng,
}
json.dump(out, open(os.path.join(WORK, "cng_deep.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print(f"\n输出 -> kv_work/cng_deep.json")
print(f"用时 {time.time()-t0:.0f}s")
