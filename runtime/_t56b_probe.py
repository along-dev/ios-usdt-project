# -*- coding: utf-8 -*-
"""T56 第 2 名复核 · **覆盖面补测**（我的主场）：
   自造**受审件未枚举**的形态，喂引擎与装置比差 —— 判"互证"是否站得住。
   ★ 只碰一次性探针库 `qk_probe_t56b*`（跑前重建／跑后 DROP）；⛔ 绝不碰 qk_e2e。
   ★ 两条读数：
     · `集合差分`（＝受审件用的那条 harm 判据：information_schema.SCHEMATA 前后差）
     · ★ `字符集`（**本条是受审件<看不到>的第二路 harm 信号**：探针库的 DEFAULT_CHARACTER_SET_NAME）
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import importlib, os, shutil, subprocess, sys, tempfile

FW = IOS_ROOT + r"\_integration\_fix_work"
DEV = os.path.join(FW, "verify_ad09_schema_migration_diff.py")
MY = os.path.join(FW, r"_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe")
PROBE = "qk_probe_t56b"

FORMS = [
    ("N-A1 ALTER DATABASE",      "ALTER DATABASE `%s` CHARACTER SET utf8mb3;" % PROBE),
    ("N-A2 ALTER SCHEMA",        "ALTER SCHEMA `%s` CHARACTER SET utf8mb3;" % PROBE),
    ("N-B  删库又建库（净 0）",   "DROP DATABASE `%s`; CREATE DATABASE `%s`;" % (PROBE, PROBE)),
    ("N-C  RENAME DATABASE",     "RENAME DATABASE `%s` TO `%s_r`;" % (PROBE, PROBE)),
    ("N-D  CREATE /*!*/ SCHEMA", "CREATE /*!50000 */ SCHEMA `%s_d`;" % PROBE),
    ("N-E  DROP /*c*/ DATABASE", "DROP /*c*/ DATABASE `%s`;" % PROBE),
]


def sql(s, db=None):
    cmd = [MY, "--skip-ssl", "-h", "127.0.0.1", "-P", "13306", "-u", "root", "-B", "-N"]
    if db:
        cmd.append(db)
    p = subprocess.run(cmd + ["-e", s], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def schemata():
    _, out, _ = sql("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA ORDER BY 1;")
    return set(out.splitlines()) if out else set()


def charset_of(db):
    _, out, _ = sql("SELECT DEFAULT_CHARACTER_SET_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='%s';" % db)
    return out or "<none>"


def reset():
    for d in (PROBE, PROBE + "_r", PROBE + "_d"):
        sql("DROP DATABASE IF EXISTS `%s`;" % d)
    sql("CREATE DATABASE `%s` DEFAULT CHARACTER SET utf8mb4;" % PROBE)


def dev_out(text):
    d = tempfile.mkdtemp(prefix="t56b_")
    shutil.copyfile(DEV, os.path.join(d, os.path.basename(DEV)))
    f = os.path.join(d, "in.sql")
    open(f, "w", encoding="utf-8").write(text)
    code = ("import sys,importlib,io;sys.path.insert(0,%r);"
            "m=importlib.import_module('verify_ad09_schema_migration_diff');"
            "sys.stdout.write(m.neutralize(io.open(%r,encoding='utf-8').read()))" % (d, f))
    env = dict(os.environ); env["AD09_TMP_DB"] = "qk_ad09_t56"
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, cwd=d)
    shutil.rmtree(d, ignore_errors=True)
    return p.returncode, (p.stdout or ""), (p.stderr or "").strip()


print("=== T56 覆盖面补测（自造形态；受审件未枚举）===")
sql("CREATE DATABASE IF NOT EXISTS `qk_ad09_t56`;")
try:
    for name, form in FORMS:
        # ---- 引擎真值（原件）
        reset()
        b = schemata(); cb = charset_of(PROBE)
        rc_r, _o, err_r = sql(form)
        a = schemata(); ca = charset_of(PROBE)
        raw_set = (a - b, b - a)
        raw_harm_metric = bool(a - b) or bool(b - a)      # ★ 受审件用的那条 harm 判据
        raw_harm_charset = (cb != ca)                     # ★ 受审件看不到的第二路
        # ---- 装置产出
        reset()
        rc_d, out, err_d = dev_out(form)
        b2 = schemata(); cb2 = charset_of(PROBE)
        rc_o, _o2, err_o = sql(out) if rc_d == 0 else (99, "", "dev fail")
        a2 = schemata(); ca2 = charset_of(PROBE)
        out_set = (a2 - b2, b2 - a2)
        out_harm_metric = bool(a2 - b2) or bool(b2 - a2)
        out_harm_charset = (cb2 != ca2)
        print("  %-24s" % name)
        print("      原件：rc=%s 集合差分=新增%s/减少%s ｜ 字符集 %s→%s ｜ 引擎报错=%s"
              % (rc_r, sorted(raw_set[0]), sorted(raw_set[1]), cb, ca, (err_r.splitlines()[-1][:40] if err_r else "无")))
        print("      产出：rc=%s %r" % (rc_d, out.replace("\n", "\\n")[:70]))
        print("            rc(引擎跑产出)=%s 集合差分=新增%s/减少%s ｜ 字符集 %s→%s ｜ 报错=%s"
              % (rc_o, sorted(out_set[0]), sorted(out_set[1]), cb2, ca2, (err_o.splitlines()[-1][:40] if err_o else "无")))
        verdict = []
        if raw_harm_metric and not out_harm_metric:
            verdict.append("★ 受审件判据可见且产出已中和")
        if raw_harm_metric and out_harm_metric:
            verdict.append("★★ 差集（产出仍有害·集合差分可见）")
        if raw_harm_charset and not out_harm_charset:
            verdict.append("★★★ **双层漏报**：原件有害（字符集被改）、装置未中和、**集合差分看不见**")
        if not raw_harm_metric and not raw_harm_charset:
            verdict.append("原件本身无害")
        print("      ⇒ %s" % ("；".join(verdict) or "—"))
finally:
    for d in (PROBE, PROBE + "_r", PROBE + "_d", "qk_ad09_t56"):
        sql("DROP DATABASE IF EXISTS `%s`;" % d)
    print("探针库残留核：", sql("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME LIKE 'qk_probe_t56b%' OR SCHEMA_NAME LIKE 'qk_ad09_t56%' OR SCHEMA_NAME LIKE 'qk_t56%';")[1] or "无 ✓")
