# -*- coding: utf-8 -*-
"""wallet-sweeper CLI：scan（只读测绘）与 sweep（归集）完全分离。

用法示例：
  # 1) 扫描目录，只查余额出报告（不接触私钥签名）
  python -m wsweep scan --scan-dir E:\\some\\dir --chains evm,tron,btc,sol -o report.json

  # 2) 归集：先 dry-run 看会发生什么
  python -m wsweep sweep --from-report report.json --to 0xTARGET

  # 3) 确认无误后真正广播
  python -m wsweep sweep --from-report report.json --to 0xTARGET --broadcast
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wsweep import chains as C
from wsweep import loader, sweep as SW
from wsweep.derive import account_from_privkey, accounts_from_mnemonic

CHAIN_CHOICES = ["evm", "tron", "btc", "sol"]


# --------------------------------------------------------------------------
# scan
# --------------------------------------------------------------------------
def cmd_scan(args) -> int:
    t0 = time.time()
    print("=" * 72)
    print("wallet-sweeper · scan（只读余额测绘）")
    print("=" * 72)

    # --- 加载输入 ---
    exts = None
    if args.exts:
        exts = {e if e.startswith(".") else "." + e for e in args.exts.split(",")}
    found, report = loader.gather(
        scan_dirs=args.scan_dir, files=args.file,
        mnemonics=args.mnemonic, privkeys=args.privkey,
        keyword=args.keyword or "", exts=exts,
    )
    print(f"\n[输入] 扫描文件 {report.files_scanned}，跳过 {report.files_skipped}，"
          f"读取 {report.bytes_read/1024:.1f} KB")
    n_mn = sum(1 for f in found if f.kind == "mnemonic")
    n_pk = sum(1 for f in found if f.kind == "privkey")
    print(f"[输入] 命中助记词 {n_mn} 条，私钥 {n_pk} 条（已按规范形式去重）")
    # 私钥变体还原汇总
    pk_items = [f for f in found if f.kind == "privkey"]
    multi = [f for f in pk_items if len(f.variants) > 1]
    if multi:
        print(f"[变体] {len(multi)} 个私钥存在多种写法，已还原为统一规范形式：")
        for f in multi[:10]:
            print(f"       {f.value[:16]}…  共 {len(f.variants)} 处写法")
            for v in f.variants[:6]:
                print(f"         · {v['origin']}   ← {os.path.basename(v['source'])}:{v['line']}")
            if len(f.variants) > 6:
                print(f"         · …另 {len(f.variants)-6} 处")
    for f in found[:20]:
        print(f"       - [{f.kind}] {f.source}:{f.line}  {f.note}")
    if len(found) > 20:
        print(f"       ... 另有 {len(found)-20} 条")
    if report.errors:
        print(f"[输入] 告警 {len(report.errors)} 条：")
        for e in report.errors[:10]:
            print(f"       ! {e}")

    if not found:
        print("\n未发现任何助记词或私钥。可用 --keyword 放宽过滤，或检查目录。")
        return 1

    # --- 派生 ---
    print(f"\n[派生] 每条助记词派生 {args.account_count} 个地址")
    accounts = []
    for f in found:
        try:
            if f.kind == "mnemonic":
                accounts.extend(accounts_from_mnemonic(
                    f.value, source=f"{f.source}:{f.line}",
                    count=args.account_count, chains=tuple(args.chains),
                    passphrase=args.passphrase))
            else:
                accounts.append(account_from_privkey(
                    f.value, source=f"{f.source}:{f.line}", chains=tuple(args.chains)))
        except Exception as exc:
            print(f"       ! 派生失败 ({f.source}:{f.line}): {exc}")
    print(f"[派生] 共 {len(accounts)} 个账户")

    # --- 查询余额 ---
    print(f"\n[查询] 链: {','.join(args.chains)}  并发 {args.workers}")
    result = C.scan_all(accounts, chains=args.chains, workers=args.workers)

    # --- 控制权与 gas 检测（多签 / 权限转移 / 7702 委托）---
    print(f"\n[控制权] 检测多签、权限转移、gas 可行性…")
    ctrl = {}
    if not args.no_control:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from . import control as CTL

        def _one(a):
            try:
                return a.evm_address or a.tron_address or a.sol_address, CTL.check_all(a, args.chains)
            except Exception as exc:
                return (a.evm_address or a.tron_address or a.sol_address,
                        {"_error": f"{type(exc).__name__}: {exc}"})

        # 外层并发设小一些：内层每条已并发 9 路，避免把公共 RPC 打爆
        outer = max(2, min(args.workers, 8))
        done = 0
        with ThreadPoolExecutor(max_workers=outer) as ex:
            futs = [ex.submit(_one, a) for a in accounts]
            for fut in as_completed(futs):
                try:
                    k, v = fut.result()
                    ctrl[k] = v
                except Exception:
                    pass
                done += 1
                if done % 50 == 0:
                    print(f"  [控制权] {done}/{len(accounts)}", flush=True)
                try:
                    k, v = fut.result()
                    ctrl[k] = v
                except Exception:
                    pass

        # 汇总风险
        risky = []
        for k, v in ctrl.items():
            tron = v.get("tron") or {}
            if tron and not tron.get("owner_ok", True):
                risky.append((k, "TRON 权限已转移", tron.get("note", "")))
            if tron.get("is_multisig"):
                risky.append((k, "TRON 多签", tron.get("note", "")))
            for cname, ev in (v.get("evm") or {}).items():
                if ev.get("is_eip7702"):
                    risky.append((k, f"EVM({cname}) EIP-7702 委托", ev.get("note", "")))
                elif ev.get("is_multisig"):
                    risky.append((k, f"EVM({cname}) 多签", ev.get("note", "")))
            sol = v.get("sol") or {}
            if sol and not sol.get("owner_ok", True):
                risky.append((k, "SOL 账户被程序托管", sol.get("note", "")))
            btc = v.get("btc") or {}
            if btc.get("is_multisig"):
                risky.append((k, "BTC 疑似多签地址", btc.get("note", "")))

        if risky:
            print(f"[控制权] 发现 {len(risky)} 项风险：")
            for k, kind, note in risky[:25]:
                print(f"         ! {kind}  {str(k)[:20]}…")
                print(f"           {note}")
        else:
            print("[控制权] 未发现权限异常")

        # gas 汇总
        gas_ok = 0
        for k, v in ctrl.items():
            tron = v.get("tron") or {}
            sol = v.get("sol") or {}
            if tron.get("gas_ok") or sol.get("gas_ok"):
                gas_ok += 1
        print(f"[控制权] gas 充足（可支付归集手续费）的账户: {gas_ok}/{len(ctrl)}")

    # --- 汇总 ---
    rows = build_rows(accounts, result)
    funded = [r for r in rows if r["has_funds"]]
    print("\n" + "=" * 72)
    print(f"扫描完成：{len(rows)} 个账户，其中 {len(funded)} 个有余额  耗时 {time.time()-t0:.0f}s")
    print("=" * 72)
    if funded:
        for r in funded[:40]:
            assets = ", ".join(f"{k}={v:,.6f}" for k, v in r["assets"].items())
            print(f"  {r['source'][:28]:28s} {r['evm_address'][:14]}...  {assets}")
    else:
        print("  未发现任何非零余额。")
    if result["errors"]:
        print(f"\n[查询] 告警 {len(result['errors'])} 条（前 8）：")
        for e in result["errors"][:8]:
            print(f"  ! {e}")

    # --- 落盘 ---
    # --- 变体还原存储 ---
    variant_store = loader.build_variant_store(found)

    # 把控制权检测结果并入每行
    key_of = lambda a: (a.evm_address or a.tron_address or a.sol_address)
    for r, a in zip(rows, accounts):
        r["control"] = ctrl.get(key_of(a), {})

    out_path = args.output or "scan_report.json"
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "chains": args.chains,
        "account_count": len(accounts),
        "funded_count": len(funded),
        "load_report": report.to_dict(),
        "query_errors": result["errors"][:100],
        "accounts": rows,
        "control": ctrl,
        # 变体还原存储：规范私钥 -> 全部原始写法与来源
        "variant_store": variant_store,
        # 归集需要私钥；scan 阶段一并保存以便 sweep 独立运行
        "secrets": [a.to_dict(include_keys=True) for a in accounts],
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"\n[输出] 报告已写入 {os.path.abspath(out_path)}")

    # --- 供 GUI 面板读取的摘要（不含私钥，仅地址与余额） ---
    try:
        summary_path = os.path.join(os.path.dirname(os.path.abspath(out_path)),
                                    "scan_summary.json")
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump({
                "generated_at": payload["generated_at"],
                "report_file": os.path.basename(out_path),
                "account_count": len(rows),
                "funded_count": len(funded),
                "rows": rows,
            }, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"[提示] 摘要落盘失败（不影响结果）: {exc}")

    # --- 密钥库（vault）落盘 ---
    try:
        vault_dir = args.vault
        os.makedirs(vault_dir, exist_ok=True)
        vault_path = os.path.join(vault_dir, "keys.json")
        with open(vault_path, "w", encoding="utf-8") as fh:
            json.dump({
                "generated_at": payload["generated_at"],
                "note": "本文件含明文私钥，请妥善保存并及时删除",
                "account_count": len(accounts),
                "variant_store": variant_store,
                "keys": payload["secrets"],
            }, fh, ensure_ascii=False, indent=2)

        # 便于人工查看的 CSV（不含完整私钥，用 fingerprint 引用）
        csv_path = os.path.join(vault_dir, "addresses.csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
            import csv as _csv
            w = _csv.writer(fh)
            w.writerow(["#", "来源", "标签", "EVM", "TRON", "BTC", "SOL",
                        "余额", "gas可用", "控制权风险"])
            for r in rows:
                c = r.get("control") or {}
                tron_c = c.get("tron") or {}
                sol_c = c.get("sol") or {}
                risks = []
                if tron_c and not tron_c.get("owner_ok", True):
                    risks.append("TRON权限转移")
                if tron_c.get("is_multisig"):
                    risks.append("TRON多签")
                for cn, ev in (c.get("evm") or {}).items():
                    if ev.get("is_eip7702"):
                        risks.append(f"{cn}:7702委托")
                    elif ev.get("is_multisig"):
                        risks.append(f"{cn}:多签")
                if sol_c and not sol_c.get("owner_ok", True):
                    risks.append("SOL被托管")
                assets = "; ".join(f"{k}={v:,.6f}" for k, v in (r.get("assets") or {}).items())
                gas = "是" if (tron_c.get("gas_ok") or sol_c.get("gas_ok")) else "否"
                w.writerow([r["index"], r["source"], r["label"], r["evm_address"],
                            r["tron_address"], r["btc_p2wpkh"], r["sol_address"],
                            assets, gas, ",".join(risks)])
        print(f"[密钥库] {os.path.abspath(vault_path)}  （含明文私钥）")
        print(f"[密钥库] {os.path.abspath(csv_path)}  （地址清单，不含私钥）")
    except Exception as exc:
        print(f"[提示] 密钥库落盘失败: {exc}")

    print("\n       下一步（dry-run）：python -m wsweep sweep --from-report "
          f"{os.path.basename(out_path)} --to <目标地址>")
    return 0


def build_rows(accounts: list, result: dict) -> list:
    """把查询结果按账户归并成行。"""
    res = result["results"]
    rows = []
    for i, acc in enumerate(accounts):
        row = {
            "index": i, "source": acc.source, "label": acc.label, "kind": acc.kind,
            "evm_address": acc.evm_address, "tron_address": acc.tron_address,
            "btc_p2wpkh": acc.btc.get("p2wpkh", ""), "sol_address": acc.sol_address,
            "assets": {}, "has_funds": False,
        }
        # EVM 各链
        evm_addr = acc.evm_address.lower()
        for cname in C.EVM_CHAINS:
            key = f"evm:{cname}"
            if key not in res:
                continue
            b = res[key].get(evm_addr)
            if not b:
                continue
            if b.get("native", 0) > 0:
                row["assets"][f"{cname}:{C.EVM_CHAINS[cname]['symbol']}"] = b["native"]
            for sym, val in (b.get("tokens") or {}).items():
                if val > 0:
                    row["assets"][f"{cname}:{sym}"] = val
        # TRON
        if acc.tron_address and "tron" in res:
            b = res["tron"].get(acc.tron_address)
            if b:
                if b.get("native", 0) > 0:
                    row["assets"]["tron:TRX"] = b["native"]
                for sym, val in (b.get("tokens") or {}).items():
                    if val > 0:
                        row["assets"][f"tron:{sym}"] = val
        # BTC（两个地址都查，合并）
        if "btc" in res:
            for addr in (acc.btc.get("p2wpkh"), acc.btc.get("p2pkh")):
                if not addr:
                    continue
                b = res["btc"].get(addr)
                if b and b.get("native", 0) > 0:
                    key = "btc:BTC" if addr == acc.btc.get("p2wpkh") else "btc:BTC(legacy)"
                    row["assets"][key] = b["native"]
        # Solana
        if acc.sol_address and "sol" in res:
            b = res["sol"].get(acc.sol_address)
            if b:
                if b.get("native", 0) > 0:
                    row["assets"]["sol:SOL"] = b["native"]
                for sym, val in (b.get("tokens") or {}).items():
                    if val > 0:
                        row["assets"][f"sol:{sym}"] = val
        row["has_funds"] = bool(row["assets"])
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
# sweep
# --------------------------------------------------------------------------
def cmd_sweep(args) -> int:
    print("=" * 72)
    mode = "!! 真实广播 !!" if args.broadcast else "dry-run（仅签名，不广播）"
    print(f"wallet-sweeper · sweep  模式: {mode}")
    print("=" * 72)

    # --- 载入报告 ---
    if not os.path.isfile(args.from_report):
        print(f"[错误] 报告不存在: {args.from_report}")
        print("       请先执行 scan 生成报告。")
        return 1
    with open(args.from_report, encoding="utf-8") as fh:
        rep = json.load(fh)

    secrets = rep.get("secrets") or []
    if not secrets:
        print("[错误] 报告中无 secrets 字段，无法归集。请用 scan 重新生成。")
        return 1

    # --- 重建账户对象（使用报告中的地址，不与链上重新派生，保证一致性）---
    from wsweep.derive import DerivedAccount
    accounts = []
    for s in secrets:
        acc = DerivedAccount(
            source=s.get("source", "report"), kind=s.get("kind", ""), label=s.get("label", ""),
            evm_address=s.get("evm_address", ""), evm_privkey=s.get("evm_privkey", ""),
            tron_address=s.get("tron_address", ""), tron_privkey=s.get("tron_privkey", ""),
            btc_privkey=s.get("btc_privkey", ""), sol_address=s.get("sol_address", ""),
            sol_privkey=s.get("sol_privkey", ""),
        )
        # BTC 三地址：报告里存的是派生结果，这里用私钥重算以保证脚本正确
        if acc.btc_privkey:
            from wsweep.derive import btc_addresses
            acc.btc = btc_addresses(int(acc.btc_privkey, 16))
        accounts.append(acc)

    # --- 只归集有余额的（除非 --all）---
    if not args.all:
        funded_addrs = {r["evm_address"].lower() for r in rep.get("accounts", []) if r.get("has_funds")}
        funded_addrs |= {r["tron_address"] for r in rep.get("accounts", []) if r.get("has_funds")}
        funded_addrs |= {r["sol_address"] for r in rep.get("accounts", []) if r.get("has_funds")}
        accounts = [a for a in accounts
                    if a.evm_address.lower() in funded_addrs
                    or a.tron_address in funded_addrs
                    or a.sol_address in funded_addrs]
        print(f"[筛选] 仅处理有余额的账户: {len(accounts)} 个（--all 可关闭此筛选）")

    if not accounts:
        print("没有需要归集的账户。")
        return 0

    # --- 目标地址解析 ---
    # 四个目标各自独立、均为可选：填了哪条链的目标地址，就只归集那条链。
    #   --to          EVM 系（ETH/BSC/Polygon/Arbitrum/Base/OP）
    #   --target-tron TRON
    #   --target-btc  BTC
    #   --target-sol  Solana
    dst_evm = (args.to or "").strip()
    dst_tron = (args.target_tron or "").strip()
    dst_btc = (args.target_btc or "").strip()
    dst_sol = (args.target_sol or "").strip()

    provided = {
        "evm": dst_evm, "tron": dst_tron, "btc": dst_btc, "sol": dst_sol,
    }
    # 只保留"既在 --chains 中、又提供了目标地址"的链
    active = [c for c in args.chains if provided.get(c)]
    skipped = [c for c in args.chains if not provided.get(c)]

    if not active:
        print("[错误] 未提供任何目标地址。至少需要 --to（EVM）或 "
              "--target-tron / --target-btc / --target-sol 之一。")
        return 2

    print(f"[目标] 本次归集链: {','.join(active)}")
    if skipped:
        print(f"[目标] 未提供目标地址，跳过: {','.join(skipped)}")

    # 格式校验（仅警告，不中止 —— 地址可能是非主流格式）
    if dst_evm and not _looks_like_evm(dst_evm):
        print(f"[警告] EVM 目标不像标准 0x 地址：{dst_evm}")
    if "tron" in active and not _looks_like_tron(dst_tron):
        print(f"[警告] TRON 目标不像 T 开头地址：{dst_tron}")
    if "btc" in active and not _looks_like_btc(dst_btc):
        print(f"[警告] BTC 目标不像 BTC 地址：{dst_btc}")
    if "sol" in active and not _looks_like_sol(dst_sol):
        print(f"[警告] Solana 目标不像 SOL 地址：{dst_sol}")

    args.chains = active

    if args.broadcast:
        print("\n" + "!" * 72)
        print("即将真实广播交易。5 秒内可按 Ctrl+C 中止。")
        print("!" * 72)
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n已中止。")
            return 130

    # --- 执行 ---
    print(f"\n[执行] 账户 {len(accounts)}  链 {','.join(active)}")
    for c in active:
        print(f"        {c:5s} -> {provided[c]}")
    plans = SW.execute(
        accounts, target_evm=dst_evm,
        target_tron=dst_tron,
        target_btc=dst_btc,
        target_sol=dst_sol,
        chains=active, tokens=args.tokens,
        broadcast=args.broadcast, leave_native=args.leave_native,
    )

    ok = [p for p in plans if p.ok]
    bad = [p for p in plans if not p.ok]
    print("\n" + "=" * 72)
    print(f"归集{'已完成' if args.broadcast else '模拟完成'}：成功 {len(ok)} 笔，跳过/失败 {len(bad)} 笔")
    print("=" * 72)
    for p in ok:
        print(f"  ✓ [{p.chain:9s}] {p.symbol:6s} {p.amount:>16,.6f}  "
              f"{p.src[:12]}... -> {p.dst[:12]}...  {p.tx_hash[:20]}")
    for p in bad:
        print(f"  ✗ [{p.chain:9s}] {p.symbol:6s} {p.src[:12]}...  原因: {p.reason}")

    # 输出文件名与报告同名派生，便于面板/GUI 稳定定位
    if args.output:
        out_path = args.output
    else:
        base = os.path.basename(args.from_report)
        if base.lower().endswith(".json"):
            base = base[:-5]
        out_path = base + ("_sweep_result.json" if args.broadcast else "_sweep_dryrun.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
            "mode": "broadcast" if args.broadcast else "dry-run",
            "chains": active,
            "targets": {c: provided[c] for c in active},
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "plans": [p.to_dict() for p in plans],
        }, fh, ensure_ascii=False, indent=2)
    print(f"\n[输出] {os.path.abspath(out_path)}")
    if not args.broadcast:
        print("       确认无误后加 --broadcast 真正执行。")
    return 0


# --------------------------------------------------------------------------
# prepare
# --------------------------------------------------------------------------
def cmd_prepare(args) -> int:
    """从 scan 报告导出三份清单：可归集 / 需撤销 / gas 不足。"""
    import csv
    if not os.path.isfile(args.from_report):
        print(f"[错误] 报告不存在: {args.from_report}")
        return 1
    j = json.load(open(args.from_report, encoding="utf-8"))
    rows = j.get("accounts", [])

    safe, risky, gasless = [], [], []
    for r in rows:
        if not r.get("has_funds"):
            continue
        c = r.get("control") or {}
        evm_c = c.get("evm") or {}
        tron_c = c.get("tron") or {}
        sol_c = c.get("sol") or {}
        btc_c = c.get("btc") or {}

        risks = []
        for cn, ev in evm_c.items():
            if ev.get("is_eip7702"):
                risks.append(f"{cn}:7702委托")
            elif ev.get("is_multisig"):
                risks.append(f"{cn}:多签")
            elif ev.get("is_contract"):
                risks.append(f"{cn}:合约")
        if tron_c and not tron_c.get("owner_ok", True):
            risks.append("tron:权限转移")
        if tron_c.get("is_multisig"):
            risks.append("tron:多签")
        if sol_c and not sol_c.get("owner_ok", True):
            risks.append("sol:被托管")
        if btc_c.get("is_multisig"):
            risks.append("btc:多签")

        gas_chains = [cn for cn, ev in evm_c.items() if ev.get("gas_ok")]
        if tron_c.get("gas_ok"):
            gas_chains.append("tron")
        if sol_c.get("gas_ok"):
            gas_chains.append("sol")

        rec = {"evm": r.get("evm_address", ""), "tron": r.get("tron_address", ""),
               "btc": r.get("btc_p2wpkh", ""), "sol": r.get("sol_address", ""),
               "assets": r.get("assets") or {}, "risks": risks,
               "gas_chains": sorted(set(gas_chains)), "source": r.get("source", "")}
        if risks:
            risky.append(rec)
        elif gas_chains:
            safe.append(rec)
        else:
            gasless.append(rec)

    os.makedirs(args.outdir, exist_ok=True)

    def w(path, recs):
        with open(os.path.join(args.outdir, path), "w", encoding="utf-8-sig",
                  newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(["EVM地址", "TRON地址", "BTC地址", "SOL地址",
                         "余额", "gas可用链", "风险", "来源"])
            for r in recs:
                a = "; ".join(f"{k}={v:,.6f}" for k, v in r["assets"].items())
                wr.writerow([r["evm"], r["tron"], r["btc"], r["sol"], a,
                             ",".join(r["gas_chains"]), ",".join(r["risks"]), r["source"]])

    w("A_safe_to_sweep.csv", safe)
    w("B_needs_revoke.csv", risky)
    w("C_no_gas.csv", gasless)
    json.dump({"safe": safe, "needs_revoke": risky, "no_gas": gasless},
              open(os.path.join(args.outdir, "plans.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"[清单] A 可安全归集（无风险 + gas 充足）: {len(safe)}")
    print(f"[清单] B 需先撤销/有风险: {len(risky)}")
    print(f"[清单] C 有余额但 gas 不足: {len(gasless)}")
    print(f"[输出] {os.path.abspath(args.outdir)}")
    return 0


# --------------------------------------------------------------------------
# revoke（EIP-7702 撤销委托）
# --------------------------------------------------------------------------
def cmd_revoke(args) -> int:
    """构造（默认不广播）EIP-7702 撤销委托交易。"""
    from . import eip7702
    if not os.path.isfile(args.from_report):
        print(f"[错误] 报告不存在: {args.from_report}")
        return 1
    j = json.load(open(args.from_report, encoding="utf-8"))
    secrets = j.get("secrets", [])
    rows = {r.get("evm_address", "").lower(): r for r in j.get("accounts", [])}

    mode = "!! 真实广播 !!" if args.broadcast else "dry-run（仅签名，不广播）"
    print("=" * 72)
    print(f"EIP-7702 撤销委托  {mode}")
    print("=" * 72)

    out = []
    for s in secrets:
        addr = (s.get("evm_address") or "").lower()
        pk = s.get("evm_privkey") or ""
        if not addr or not pk:
            continue
        row = rows.get(addr) or {}
        ctrl = (row.get("control") or {}).get("evm") or {}
        delegated = [cn for cn, ev in ctrl.items() if ev.get("is_eip7702")]
        if not delegated:
            continue

        for ch in args.chains:
            if ch not in delegated:
                continue
            cfg = C.EVM_CHAINS.get(ch)
            if not cfg:
                continue
            rpc = cfg["rpc"]
            nc, _ = C.rpc_single(rpc, "eth_getTransactionCount", [addr, "latest"])
            gp, _ = C.rpc_single(rpc, "eth_gasPrice", [])
            bal, _ = C.rpc_single(rpc, "eth_getBalance", [addr, "latest"])
            nonce = int(nc, 16) if nc else 0
            gas_price = int(gp, 16) if gp else 20_000_000_000
            balance = int(bal, 16) / 1e18 if bal and bal != "0x" else 0.0
            est = eip7702.estimate_revoke_cost(gas_price)
            affordable = balance > est

            rec = {
                "address": addr, "chain": ch, "nonce": nonce,
                "gas_price_gwei": round(gas_price / 1e9, 4),
                "balance": balance, "est_cost": est,
                "affordable": affordable,
                "current_delegate": (ctrl.get(ch) or {}).get("delegate_to", ""),
            }

            if not affordable:
                rec["status"] = "跳过：gas 不足，需先注入原生币"
                out.append(rec)
                continue

            signed = eip7702.sign_revoke_tx(pk, cfg["chain_id"], nonce, gas_price)
            rec["sign_ok"] = signed.get("ok", False)
            rec["tx_hash"] = signed.get("tx_hash", "")
            rec["raw"] = signed.get("raw", "")
            if signed.get("ok") and args.broadcast:
                sent, err = C.rpc_single(rpc, "eth_sendRawTransaction", [signed["raw"]])
                rec["broadcast"] = bool(sent)
                rec["broadcast_result"] = sent or str(err)
                rec["status"] = "已广播" if sent else f"广播失败: {err}"
            elif signed.get("ok"):
                rec["status"] = "已签名（dry-run，未广播）"
            else:
                rec["status"] = f"签名失败: {signed.get('error')}"
            out.append(rec)

    ok = [r for r in out if r.get("sign_ok")]
    skip = [r for r in out if not r.get("sign_ok")]
    print(f"\n[结果] 构造 {len(ok)} 笔，跳过/失败 {len(skip)} 笔")
    for r in ok:
        print(f"  ✓ [{r['chain']:9s}] nonce={r['nonce']:6d}  "
              f"成本 {r['est_cost']:.8f}  {r['status']}")
        print(f"      {r['address']}  当前委托 {r['current_delegate'][:20]}")
    for r in skip:
        print(f"  ✗ [{r['chain']:9s}] {r['address']}  {r['status']}")

    json.dump(out, open(args.output, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n[输出] {os.path.abspath(args.output)}")
    if not args.broadcast:
        print("       注意：撤销交易本身也可能被 drainer 拦截，广播前请确认抢跑/私有通道方案。")
    return 0


def _looks_like_evm(a: str) -> bool:
    a = (a or "").strip()
    if a.startswith(("0x", "0X")):
        a = a[2:]
    return len(a) == 40 and all(c in "0123456789abcdefABCDEF" for c in a)


def _looks_like_tron(a: str) -> bool:
    return bool(a) and a.startswith("T") and len(a) == 34


def _looks_like_btc(a: str) -> bool:
    return bool(a) and (a.startswith(("bc1", "1", "3")) and len(a) >= 26)


def _looks_like_sol(a: str) -> bool:
    return bool(a) and 32 <= len(a) <= 44 and not a.startswith(("0x", "bc1", "T"))


# --------------------------------------------------------------------------
# generate（辅助：生成测试助记词）
# --------------------------------------------------------------------------
def cmd_generate(args) -> int:
    from wsweep.derive import generate_mnemonic
    for _ in range(args.count):
        print(generate_mnemonic(args.strength))
    return 0


# --------------------------------------------------------------------------
# 参数解析
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wsweep",
        description="本地钱包多链余额测绘与归集工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- scan ---
    s = sub.add_parser("scan", help="只读扫描：提取助记词/私钥并查询多链余额")
    s.add_argument("--scan-dir", action="append", default=[],
                   help="递归扫描的目录（可重复）")
    s.add_argument("--file", action="append", default=[],
                   help="指定文件或目录（可重复）")
    s.add_argument("--mnemonic", action="append", default=[], help="命令行直接传入助记词")
    s.add_argument("--privkey", action="append", default=[], help="命令行直接传入私钥 hex")
    s.add_argument("--keyword", default="",
                   help="关键词过滤（正则）。留空则扫描所有文本类文件")
    s.add_argument("--exts", default="",
                   help="限定扩展名，逗号分隔，如 txt,json,env")
    s.add_argument("--chains", default="evm,tron,btc,sol",
                   help="启用链，逗号分隔（evm,tron,btc,sol）")
    s.add_argument("--account-count", type=int, default=5,
                   help="每条助记词派生的地址数（默认 5）")
    s.add_argument("--passphrase", default="", help="BIP39 passphrase（第 25 个词）")
    s.add_argument("--workers", type=int, default=6, help="并发查询线程数")
    s.add_argument("--no-control", action="store_true",
                   help="跳过多签/权限/gas 控制权检测")
    s.add_argument("--vault", default="vault",
                   help="密钥库输出目录（默认 vault/，相对当前目录）")
    s.add_argument("-o", "--output", default="", help="报告输出路径")
    s.set_defaults(func=cmd_scan)

    # --- sweep ---
    w = sub.add_parser("sweep", help="归集：把余额转到目标地址")
    w.add_argument("--from-report", required=True, help="scan 生成的报告路径")
    w.add_argument("--to", default="", help="EVM 系目标地址（ETH/BSC/Polygon/Arbitrum/Base/OP）")
    w.add_argument("--target-tron", default="", help="TRON 目标地址（T 开头）")
    w.add_argument("--target-btc", default="", help="BTC 目标地址（bc1 / 1 / 3 开头）")
    w.add_argument("--target-sol", default="", help="Solana 目标地址（Base58）")
    w.add_argument("--chains", default="evm,tron,btc,sol", help="归集哪些链")
    w.add_argument("--tokens", default="", help="仅归集这些代币符号，逗号分隔（留空=全部）")
    w.add_argument("--leave-native", type=float, default=None,
                   help="每条 EVM 链保留的 native 数量（默认自动）")
    w.add_argument("--all", action="store_true", help="不筛选，处理全部账户")
    w.add_argument("--broadcast", action="store_true",
                   help="真正广播交易（默认 dry-run，仅签名不发送）")
    w.add_argument("-o", "--output", default="", help="结果输出路径")
    w.set_defaults(func=cmd_sweep)

    # --- generate ---
    g = sub.add_parser("generate", help="生成合规 BIP39 助记词（测试用）")
    g.add_argument("--count", type=int, default=1)
    g.add_argument("--strength", type=int, default=128, choices=[128, 160, 192, 224, 256])
    g.set_defaults(func=cmd_generate)

    # --- prepare ---
    pr = sub.add_parser("prepare", help="从 scan 报告导出可归集清单（不广播）")
    pr.add_argument("--from-report", required=True, help="scan 生成的报告")
    pr.add_argument("-o", "--outdir", default="prepare", help="输出目录")
    pr.set_defaults(func=cmd_prepare)

    # --- revoke ---
    rv = sub.add_parser("revoke", help="构造 EIP-7702 撤销委托交易（默认只签名不广播）")
    rv.add_argument("--from-report", required=True, help="scan 生成的报告")
    rv.add_argument("--chains", default="eth,bsc,polygon,arbitrum,base,optimism",
                    help="要撤销的 EVM 链")
    rv.add_argument("--broadcast", action="store_true",
                    help="真正广播撤销交易（默认 dry-run，仅签名）")
    rv.add_argument("-o", "--output", default="revoke_plan.json", help="结果输出路径")
    rv.set_defaults(func=cmd_revoke)

    return p


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    # 规范化链参数
    # revoke 的 --chains 是具体 EVM 链名（eth/bsc/...），不是 evm/tron/btc/sol 分组
    if getattr(args, "chains", None):
        if isinstance(args.chains, str):
            args.chains = [c.strip() for c in args.chains.split(",") if c.strip()]
        if args.cmd == "revoke":
            bad = [c for c in args.chains if c not in C.EVM_CHAINS]
            if bad:
                print(f"[错误] 未知 EVM 链: {', '.join(bad)}"
                      f"（可选: {','.join(C.EVM_CHAINS)}）")
                return 2
        else:
            bad = [c for c in args.chains if c not in CHAIN_CHOICES]
            if bad:
                print(f"[错误] 未知链: {', '.join(bad)}（可选: {','.join(CHAIN_CHOICES)}）")
                return 2
    if getattr(args, "tokens", None) and isinstance(args.tokens, str):
        args.tokens = [t.strip() for t in args.tokens.split(",") if t.strip()] or None

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
