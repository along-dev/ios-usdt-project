# -*- coding: utf-8 -*-
"""T27 §五 V2 补做 —— 负控：倒回 cleanup() 的反向减回 ⇒ V1 的观测量必须动（＝V1 能红）。

★ 同名量对照：同一观测量（qk_e2e_test 的 custom.usdt_num / agent.usdt_num 快照）
    A 现版判据（含反向减回） ⇒ 期望 Δ=0（＝V3，绿）
    B 倒回版（临时副本，去 _undo_accumulation） ⇒ 期望 Δ≠0（＝V1 有条件变红）
★ 硬闸：目标库必须是 qk_e2e_test；⛔ 绝不等于业务库 qk_e2e。
★ 全程持锁（iso_run.acquire_lock）⇒ 防并发（F-10 形态）。
"""
import os, sys, hashlib, subprocess, tempfile, shutil, json

FW = r"E:\ios漏洞\_integration\_fix_work"
sys.path.insert(0, FW)
import iso_run as R

DST, SRC, API = R.DST_DB, R.SRC_DB, R.ISO_API
assert DST == "qk_e2e_test", DST
assert SRC == "qk_e2e", SRC
assert DST != SRC
print(f"★ 硬闸通过：目标库={DST} ≠ 护栏库={SRC}；API={API}")


def q(stmt, db=DST):
    p = subprocess.run([R.MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", "13306", "-u", "root",
                        "--default-character-set=utf8mb4", "-B", "-e", f"USE {db}; {stmt}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [l for l in (p.stdout or "").strip().splitlines() if l.strip()]


def col_snapshot(tag):
    """观测量快照：两列的 (user_id, usdt_num) 逐行 + 其 sha256。"""
    rows = q("SELECT CONCAT('custom:',user_id,':',COALESCE(usdt_num,'<NULL>')) FROM custom "
             "UNION ALL SELECT CONCAT('agent:',user_id,':',COALESCE(usdt_num,'<NULL>')) FROM agent "
             "ORDER BY 1;")
    h = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
    print(f"  [{tag}] {len(rows)} 行 · sha256={h}")
    for r in rows:
        print(f"        {r}")
    return h, rows


def run_crit(path, label):
    env = {**os.environ, "DSH_DB": DST, "DSH_API": API}
    assert env["DSH_DB"] != SRC, "⛔ 子进程 DSH_DB 落回业务库！中止"
    p = subprocess.run([sys.executable, path], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    lines = (p.stdout or "").splitlines()
    res = [l for l in lines if l.startswith("RESULT=")]
    tgt = [l for l in lines if "连接目标" in l]
    print(f"  [{label}] EXIT={p.returncode}  {res[-1] if res else '(无 RESULT 行)'}")
    if tgt:
        print(f"        {tgt[0].strip()}")
    return p.returncode, (res[-1] if res else None)


summary = {}
R.acquire_lock()
print("★ 已持锁（防并发）")
try:
    R.start_iso()
    ok, body = R.wait_health()
    print(f"  [health] {API}/health ⇒ {body[:80] if ok else body}")
    if not ok:
        print("★ 实例未就绪 ⇒ 中止"); sys.exit(2)

    # 播种（复刻 iso_run main 的顺序：起实例 → 克隆结构 → 种行）
    for tag, argv in (("schema", ["--schema-only"]), ("rows", [])):
        sp = subprocess.run([sys.executable, os.path.join(FW, "seed_test_db.py"), *argv],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env={**os.environ, "DSH_DB": DST, "DSH_SEED_FROM": SRC})
        print(f"  [seed/{tag}] EXIT={sp.returncode}")

    R.set_fixture_cuid(201)
    print(f"  [fixture] packet.custom_user_id = {R.fixture_cuid()}（绑定态）")

    # ---- A：现版（含反向减回）----
    a0 = col_snapshot("A/before")
    ra = run_crit(os.path.join(FW, "verify_f1c9_toaddress_guard.py"), "A 现版")
    a1 = col_snapshot("A/after")
    deltaA = (a0[0] != a1[0])
    print(f"  ⇒ A: 观测量变化 = {deltaA}（期望 False ＝ 修复有效）")
    summary["A_fixed"] = {"exit": ra[0], "result": ra[1], "delta": deltaA,
                          "sha_before": a0[0], "sha_after": a1[0]}

    # ---- B：倒回版（临时副本，去 _undo_accumulation）----
    src = os.path.join(FW, "verify_f1c9_toaddress_guard.py")
    orig = open(src, encoding="utf-8").read()
    orig_sha = hashlib.sha256(orig.encode("utf-8")).hexdigest()
    needle = '    _undo_accumulation("i2c1-f1c9-")\n'
    assert orig.count(needle) == 1, f"★ 变异针命中 {orig.count(needle)} 次（须恰 1 次）⇒ 中止"
    mutant = orig.replace(needle, '    # [V2 变异] _undo_accumulation 已移除\n', 1)
    assert mutant != orig
    tdir = tempfile.mkdtemp(prefix="v2mutant_")
    mpath = os.path.join(tdir, "verify_f1c9_toaddress_guard.py")
    open(mpath, "w", encoding="utf-8").write(mutant)
    print(f"  [B] 临时副本={mpath}（源件 sha 不变：{hashlib.sha256(open(src,'rb').read()).hexdigest()[:16]}）")
    assert hashlib.sha256(open(src, "rb").read()).hexdigest() == orig_sha, "★ 源件被动过！"

    b0 = col_snapshot("B/before")
    rb = run_crit(mpath, "B 倒回版")
    b1 = col_snapshot("B/after")
    deltaB = (b0[0] != b1[0])
    print(f"  ⇒ B: 观测量变化 = {deltaB}（期望 True ＝ V1 有条件变红 ⇒ 判别力成立）")
    summary["B_mutated"] = {"exit": rb[0], "result": rb[1], "delta": deltaB,
                            "sha_before": b0[0], "sha_after": b1[0],
                            "rows_before": b0[1], "rows_after": b1[1]}

    # ---- 复位 ----
    R.set_fixture_cuid(201)
    print(f"  [复位] packet.custom_user_id = {R.fixture_cuid()}")
    shutil.rmtree(tdir, ignore_errors=True)
    print("  [清理] 临时副本已删")

    print("\n=== V2 判据 ===")
    print(f"  A 现版      Δ={deltaA}  (期望 False)")
    print(f"  B 倒回版    Δ={deltaB}  (期望 True)")
    verdict = (not deltaA) and deltaB
    print(f"  V2 = {'PASS（判别力成立：倒回即红、不倒回不红）' if verdict else 'FAIL'}")
    summary["V2"] = "PASS" if verdict else "FAIL"
finally:
    R.stop_iso()
    R.release_lock()
    print("★ 实例已停 · 锁已释放")

print("SUMMARY_JSON=" + json.dumps(summary, ensure_ascii=False))
