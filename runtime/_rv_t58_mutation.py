# -*- coding: utf-8 -*-
"""T58 · ④ 独立变异（我自造，定向）：只对含 `DROP DATABASE` 的输入恒等 ⇒
   应【只】让 DROP 类形态报差集、其余形态保持 ✓ ⇒ 证判据**非恒绿 ＋ 有分辨力**。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import importlib, io, os, shutil, sys, tempfile

sys.path.insert(0, IOS_ROOT + r"\_integration\_fix_work")
V = importlib.import_module("verify_migration_independent")

REAL = os.path.abspath(V.DEFAULT_DEVICE)
md = tempfile.mkdtemp(prefix="rv58_mut_")
mut = os.path.join(md, os.path.basename(V.DEFAULT_DEVICE))
with io.open(mut, "w", encoding="utf-8") as fh:
    fh.write(
        "import importlib.util as U\n"
        "_s = U.spec_from_file_location('_rv58_real', %r)\n"
        "_m = U.module_from_spec(_s); _s.loader.exec_module(_m)\n"
        "globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})\n"
        "_real = _m.neutralize\n"
        "def neutralize(t):\n"
        "    if 'DROP DATABASE' in t:   # ★ 我的定向洞：只放过 DROP DATABASE\n"
        "        return t\n"
        "    return _real(t)\n" % REAL)

FORMS = [
    ("D1 DROP DATABASE",  "DROP DATABASE `%s`;" % V.PROBE_DB),
    ("D2 CREATE DATABASE", "CREATE DATABASE `%s2`;" % V.PROBE_DB),
    ("D7 ALTER 改属性",    "ALTER DATABASE `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;" % V.PROBE_DB),
    ("M1 真多语句 DROP",   "SET @x:=1;\nDROP DATABASE `%s`;\nSELECT 1;" % V.PROBE_DB),
]
print("== ④ 定向变异 vs 原件：逐形态看【引擎差分】（★ 判据的信号）==")
for name, sql in FORMS:
    V.reset_probe(True); _tn, _tg, _tc = V.engine_dd_effect(sql)     # 原件 ground truth
    V.reset_probe(True); rcA, outA, _ = V.dev_neutralize(REAL, sql)
    a_n, a_g, a_c = V.engine_dd_effect(outA)
    V.reset_probe(True); rcM, outM, _ = V.dev_neutralize(mut, sql)
    m_n, m_g, m_c = V.engine_dd_effect(outM)
    harmA = bool(a_n or a_g or a_c); harmM = bool(m_n or m_g or m_c)
    print("  %-18s 原件产出有害=%-5s ｜ 变异产出有害=%-5s  %s"
          % (name, harmA, harmM, "⇒ ★变异被抓(红)" if harmM else "⇒ 变异未被抓(绿)"))
    for suf in ("2", "3", "4"):
        V.run_sql("DROP DATABASE IF EXISTS `%s%s`;" % (V.PROBE_DB, suf))
V.reset_probe(False)
shutil.rmtree(md, ignore_errors=True)
print()
print("★ 判读：若【只有含 DROP DATABASE 的形态】变红 ⇒ 判据非恒绿且**有分辨力** ✓")
print("★ 残留 qk_t56_* =", [x for x in __import__("re").findall(r"qk_t56\w*", "")] or "见 §⑥ 现查")
