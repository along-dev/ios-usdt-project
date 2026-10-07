#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
D4-C2 判据：R-06 批量脱敏（11-payment 的 3+1 类凭据）V1-V8。

动前红 / 动后绿。

用法:
    python verify_d4c2_credentials.py            # 全量判定 (V1-V8)
    python verify_d4c2_credentials.py --snapshot # 只写 base 快照

V4 保形证明（严格）:
    对每个被改文件, 取 _d4c2_work/backup/<rel> 的原始字节, 把其中的原凭据
    按同一映射替换 -> 必须与当前字节 **逐字节相等**; 且反向 (把伪值还原为原值)
    也必须相等。此外逐行比对: 行数不变, 且每个差异行必含 REDACTED。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import sys

# ★ X3：本脚本自带 UTF-8 输出（P-10）
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = USDT_ROOT
PAY = os.path.join(ROOT, "11-payment")
WORK = os.path.join(ROOT, "_d4c2_work")
BACKUP = os.path.join(WORK, "backup")
BASE_JSON = os.path.join(WORK, "base.json")
PY = r"E:\CTF\runtime\python\python.exe"

# --- 3+1 类凭据: 原值 -> 伪值 ---
JWT1 = (b"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOjEzNzEsIm5hbWUiOiJcdTUxYTBcdTUxOWIi"
        b"LCJ0eXBlIjoibWVyY2hhbnQiLCJqdGkiOiI1ODE1N2I1YTcxYzNjNjI1YjA4OGQ3MTdkZmE0N2RhMiIs"
        b"Im5iZiI6MTc5MDMxNTQzMCwiZXhwIjoxNzkwNDAxODMwfQ.K2HSODMnHfqw5boNDTI2lMowkD0UsnHcJ1IG2EmYxoM")
JWT2 = (b"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOjEzNzEsIm5hbWUiOiJcdTUxYTBcdTUxOWIi"
        b"LCJ0eXBlIjoibWVyY2hhbnQiLCJqdGkiOiI5OGNmYTk3NDEyODdmMjMyNmJmMzY5NmM1MWI3ZGY0OCIs"
        b"Im5iZiI6MTc5MDI3NTc0MSwiZXhwIjoxNzkwMzYyMTQxfQ.9f_UdxZPzNKhsChGFaLSWNz3hovTPRmJjN2A5pEzNCU")
JWT3 = (b"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOjEzNzEsIm5hbWUiOiJcdTUxYTBcdTUxOWIi"
        b"LCJ0eXBlIjoibWVyY2hhbnQiLCJqdGkiOiIxYWY3NWNmODUyNDZmNDg3YTViZDFkMzk2Yjc2NGViMiIs"
        b"Im5iZiI6MTc5MDI3NTkwMSwiZXhwIjoxNzkwMzYyMzAxfQ.Izxw63V1TIc9WQ7_BlTAQgEl7UnwHA3P4BHkJrnSbbw")

RED_PW = b"<REDACTED_PASSWORD>"
RED_JWT = b"<REDACTED_JWT>"
RED_AK = b"<REDACTED_ACCESSKEY>"
RED_SK = b"<REDACTED_SECRETKEY>"

# (orig, repl) —— 顺序无关, 因各原值互不为子串
MAPPING = [
    (b"HJAOxU46", RED_PW),
    (b"BlVnlKWzllSGLm47BkWahzRq", RED_AK),
    (b"MXeRGbN9nWUnpPPrAq4zTV6k", RED_AK),
    (b"0r3W6Br2y8HK9VGzm5J9HXDwopY0J7SqeN6yzYqM", RED_SK),
    (JWT1, RED_JWT),
    (JWT2, RED_JWT),
    (JWT3, RED_JWT),
]
ORIGINALS = [o for o, _ in MAPPING]
JWT_ORIGINALS = [JWT1, JWT2, JWT3]

# ★★ T89（⌛2026-10-06）：本表与 `E:\USDT项目\rollback.ps1` 的 `$GUARDS`
#    **钉的是同一批件的内容 sha** ⇒ ★★ **两处必须同步改**。
#    ⛔ 只改一处 ⇒ 另一处必报「不匹配」：本判据 `V8` **FAIL** ／ `rollback.ps1 -Guard` 报 `VIOLATED`。
#    ★ 重算一条命令（★ 在仓库根跑，把路径换成要重算的件）：
#      python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" 09-docs/spec/contracts.md
#    ★ 口径：**本表写<大写>**（比对时 `.hexdigest().upper()`）；
#      **`rollback.ps1` 的 `Expect` 写<小写>**（比对时 `.Hash.ToLower()`）⇒ ⛔ 别照抄。
AUTH_BASELINE = {
    r"09-docs\spec\contracts.md": "0E03048DDFBE6945DBA0CFDA5C9DAE17B3B50B9AC485A83F921913E49E337358",
    r"_manifest.sha256": "B940DC19A76F1627ED185F9AF54FF79F0F3DAC4FCECE0F86F78C3C9CDBDB58C2",
}

# 卡的 28 文件目标集 (V4 保形 + V7 eol 的范围)
BASE_TARGETS = {
    r"11-payment\cxlogin.py", r"11-payment\pw_agent.py", r"11-payment\pw_auth.py",
    r"11-payment\pw_axios.py", r"11-payment\pw_clean.py", r"11-payment\pw_confirm.py",
    r"11-payment\pw_dash.py", r"11-payment\pw_deep.py", r"11-payment\pw_find_dec.py",
    r"11-payment\pw_fund.py", r"11-payment\pw_fund2.py", r"11-payment\pw_headed.py",
    r"11-payment\pw_hook.py", r"11-payment\pw_login.py", r"11-payment\pw_login2.py",
    r"11-payment\pw_matrix.py", r"11-payment\pw_matrix2.py", r"11-payment\pw_pages.py",
    r"11-payment\pw_plain.py", r"11-payment\pw_privesc.py", r"11-payment\pw_privesc2.py",
    r"11-payment\pw_routes.py", r"11-payment\pw_scripts.py", r"11-payment\pw_settings.py",
    r"11-payment\all_plain.json", r"11-payment\dash_net.json",
    r"11-payment\pages_dump.json", r"11-payment\apidoc.txt",
}

results = []


def chk(name, ok, detail=""):
    results.append((name, ok, detail))
    print("  [%s] %-4s %s" % ("PASS" if ok else "FAIL", name, detail))


def eol_of(b):
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    cr = b.count(b"\r") - crlf
    if crlf and (lf or cr):
        return "MIXED"
    if crlf:
        return "CRLF"
    if lf:
        return "LF"
    if cr:
        return "CR"
    return "NONE"


def walk_pay():
    """递归 11-payment/** 全部文件（不排除 __pycache__）. """
    out = []
    for dp, dn, fns in os.walk(PAY):
        for fn in fns:
            out.append(os.path.join(dp, fn))
    return sorted(out)


def reverse_restore(cur):
    """
    把伪值还原为原值, 返回所有可能的还原结果集合。
    PASSWORD/SECRETKEY 各只有 1 个原值 -> 直接替换。
    ACCESSKEY 有 2 个原值、JWT 有 3 个原值, 且同一行可能混用/不含其中某类
    -> 逐位置穷举所有 (AK, JWT) 组合, 保证不漏解。
    """
    AK_ORIG = [b"BlVnlKWzllSGLm47BkWahzRq", b"MXeRGbN9nWUnpPPrAq4zTV6k"]
    base = cur.replace(RED_PW, b"HJAOxU46") \
              .replace(RED_SK, b"0r3W6Br2y8HK9VGzm5J9HXDwopY0J7SqeN6yzYqM")
    ak_n = base.count(RED_AK)
    jwt_n = base.count(RED_JWT)
    if ak_n == 0 and jwt_n == 0:
        return {base}
    # 同一文件的多个占位符在实践中同一值重复出现(同文件同 token),
    # 故只穷举"取值集合"而非逐位置笛卡尔积: 尝试 (AK 全同) x (JWT 全同)。
    variants = set()
    ak_opts = AK_ORIG if ak_n else [None]
    jwt_opts = JWT_ORIGINALS if jwt_n else [None]
    for a in ak_opts:
        for j in jwt_opts:
            s = base
            if a is not None:
                s = s.replace(RED_AK, a)
            if j is not None:
                s = s.replace(RED_JWT, j)
            variants.add(s)
    # 混合情形: 同文件内 AK#1 与 AK#2 并存 (apidoc.txt) -> 逐位置穷举 (上限 2^ak_n, n<=7 可控)
    if ak_n and ak_n <= 8:
        for picks in itertools.product(AK_ORIG, repeat=ak_n):
            s = base
            for a in picks:
                s = s.replace(RED_AK, a, 1)
            for j in (JWT_ORIGINALS if jwt_n else [None]):
                if j is not None:
                    s = s.replace(RED_JWT, j)
                variants.add(s)
    return variants


def forward_redact(orig):
    b = orig
    for o, r in MAPPING:
        b = b.replace(o, r)
    return b


def main():
    if "--snapshot" in sys.argv:
        base = {}
        for p in walk_pay():
            b = open(p, "rb").read()
            base[os.path.relpath(p, ROOT)] = {
                "sha256": hashlib.sha256(b).hexdigest(),
                "bytes": len(b),
                "eol": eol_of(b),
            }
        os.makedirs(WORK, exist_ok=True)
        json.dump(base, open(BASE_JSON, "w"), indent=1, sort_keys=True)
        print("snapshot: %s (%d files)" % (BASE_JSON, len(base)))
        return 0

    print("=" * 74)
    print("D4-C2 判据  V1-V8   11-payment 凭据脱敏 (PASSWORD / JWT / ACCESSKEY x2 / SECRETKEY)")
    print("=" * 74)

    base = json.load(open(BASE_JSON)) if os.path.exists(BASE_JSON) else {}

    # 裁决 B 的前置: 移除 __pycache__ (编译缓存, 可再生), 使其不污染 V1/V2/V7 的判定。
    # 必须在任何 py_compile 之前执行; V5 已改为写临时目录, 不会重建它。
    pcd = os.path.join(PAY, "__pycache__")
    pycache_removed = False
    if os.path.isdir(pcd):
        shutil.rmtree(pcd, ignore_errors=True)
        pycache_removed = not os.path.exists(pcd)

    files = walk_pay()

    # ---- V1 ----
    hits = [os.path.relpath(p, ROOT) for p in files if b"HJAOxU46" in open(p, "rb").read()]
    chk("V1", not hits, "递归 %d 文件不含 HJAOxU46; 残留: %s" % (len(files), hits or "无"))

    # ---- V2 ----
    jh = []
    for p in files:
        b = open(p, "rb").read()
        for n, t in enumerate(JWT_ORIGINALS, 1):
            if t in b:
                jh.append("%s:JWT%d" % (os.path.relpath(p, ROOT), n))
    chk("V2", not jh, "递归 %d 文件不含原 JWT x3; 残留: %s" % (len(files), jh or "无"))

    # ---- V3 ----
    ab = open(os.path.join(PAY, "apidoc.txt"), "rb").read()
    v3 = []
    if b"BlVnlKWzllSGLm47BkWahzRq" in ab:
        v3.append("AccessKey#1")
    if b"MXeRGbN9nWUnpPPrAq4zTV6k" in ab:
        v3.append("AccessKey#2")
    if b"0r3W6Br2y8HK9VGzm5J9HXDwopY0J7SqeN6yzYqM" in ab:
        v3.append("SecretKey")
    chk("V3", not v3, "apidoc.txt 不含原 AccessKey#1/#2 与 SecretKey; 残留: %s" % (v3 or "无"))

    # ---- V4: 保形 (范围 = 卡的 28 文件目标集; __pycache__ 已按裁决 B 删除, 不在保形范围) ----
    v4bad = []
    v4rows = []
    for rel in sorted(base):
        if rel not in BASE_TARGETS:
            continue
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            v4bad.append("%s 消失" % rel)
            continue
        cur = open(p, "rb").read()
        if hashlib.sha256(cur).hexdigest() == base[rel]["sha256"]:
            continue
        bak = os.path.join(BACKUP, rel)
        if not os.path.exists(bak):
            v4bad.append("%s 无备份" % rel)
            continue
        orig = open(bak, "rb").read()
        # (a) 正推: orig 经映射 == cur
        if forward_redact(orig) != cur:
            v4bad.append("%s 正推不等" % rel)
            continue
        # (b) 逆推: cur 逆还原 == orig
        if orig not in reverse_restore(cur):
            v4bad.append("%s 逆推不等" % rel)
            continue
        # (c) 行数不变
        ol = orig.splitlines(keepends=True)
        cl = cur.splitlines(keepends=True)
        if len(ol) != len(cl):
            v4bad.append("%s 行数 %d->%d" % (rel, len(ol), len(cl)))
            continue
        # (d) 差异行必含 REDACTED 且逆还原后等于原行
        ndiff = 0
        for i, (a, b_) in enumerate(zip(ol, cl), 1):
            if a == b_:
                continue
            ndiff += 1
            if b"REDACTED" not in b_:
                v4bad.append("%s L%d 差异行无 REDACTED" % (rel, i))
                break
            if a not in reverse_restore(b_):
                v4bad.append("%s L%d 逆还原不符" % (rel, i))
                break
        v4rows.append((rel, ndiff))
    if not v4bad:
        det = "; ".join("%s:%d行" % (r.replace("11-payment\\", ""), n) for r, n in v4rows)
        chk("V4", True, "保形 OK, %d/%d 目标文件被改, 逐行 diff: %s"
            % (len(v4rows), len(BASE_TARGETS), det))
    else:
        chk("V4", False, "; ".join(v4bad[:8]))

    # ---- V5 ----
    # 注意: py_compile 默认会在源文件旁生成 __pycache__, 污染 11-payment 树
    # -> 用 py_compile.compile(cfile=临时路径) 避免写回源码目录。
    pyf = [p for p in files if p.endswith(".py")]
    bad5 = []
    tmpd = tempfile.mkdtemp(prefix="d4c2_pyc_")
    for p in pyf:
        dst = os.path.join(tmpd, hashlib.md5(p.encode()).hexdigest() + ".pyc")
        r = subprocess.run(
            [PY, "-c",
             "import py_compile,sys; py_compile.compile(sys.argv[1], cfile=sys.argv[2], doraise=True)",
             p, dst],
            capture_output=True)
        if r.returncode != 0:
            bad5.append("%s(%s)" % (os.path.basename(p),
                                    r.stderr.decode("utf-8", "replace").strip().splitlines()[-1][:80]))
    shutil.rmtree(tmpd, ignore_errors=True)
    chk("V5", not bad5, "py_compile %d 个 .py: %s" % (len(pyf), bad5 or "全部通过"))

    # ---- V6 ----
    jsf = [p for p in files if p.endswith(".json")]
    bad6 = []
    for p in jsf:
        try:
            json.loads(open(p, "rb").read().decode("utf-8"))
        except Exception as e:
            bad6.append("%s(%s)" % (os.path.basename(p), e))
    chk("V6", not bad6, "json.loads %d 个 .json: %s" % (len(jsf), bad6 or "全部通过"))

    # ---- V7: eol 与 base 一致 (28 目标文件逐文件二进制核对 + __pycache__ 已删) ----
    bad7 = []
    for rel in sorted(BASE_TARGETS):
        meta = base.get(rel)
        p = os.path.join(ROOT, rel)
        if meta is None:
            bad7.append("%s 不在 base" % rel)
            continue
        if not os.path.exists(p):
            bad7.append("%s 消失" % rel)
            continue
        e = eol_of(open(p, "rb").read())
        if e != meta["eol"]:
            bad7.append("%s %s->%s" % (rel, meta["eol"], e))
    # 裁决 B: __pycache__ 必须已删除, 且 V5 运行后不得被重建
    pcd = os.path.join(PAY, "__pycache__")
    if os.path.exists(pcd):
        bad7.append("__pycache__ 仍存在(裁决B未执行或被重建)")
    hook = base.get(r"11-payment\pw_hook.py", {}).get("eol")
    chk("V7", not bad7,
        "eol 核对 %d 目标文件一致 (pw_hook base=%s); __pycache__ 已删且 V5 后未重建; 异动: %s"
        % (len(BASE_TARGETS), hook, bad7 or "无"))

    # ---- V8 ----
    bad8 = []
    for rel, want in AUTH_BASELINE.items():
        got = hashlib.sha256(open(os.path.join(ROOT, rel), "rb").read()).hexdigest().upper()
        if got != want:
            bad8.append("%s %s" % (rel, got[:16]))
    chk("V8", not bad8, "守护: %s" % (bad8 or "_manifest.sha256 + contracts.md 未改"))

    npass = sum(1 for _, ok, _ in results if ok)
    print("-" * 74)
    print("结果: %d/%d PASS" % (npass, len(results)))
    fail = [n for n, ok, _ in results if not ok]
    if fail:
        print("!! 失败: %s" % ", ".join(fail))
    print("=" * 74)
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
