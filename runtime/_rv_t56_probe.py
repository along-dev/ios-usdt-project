# -*- coding: utf-8 -*-
"""复核 T56 · 独立实证：① --device 是否真说了算（自陈 bug#1）② 净0 盲区。只读 + 只在探针库上建删。"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os, sys, shutil, tempfile
sys.path.insert(0, IOS_ROOT + r"\_integration\_fix_work")
import importlib
T = importlib.import_module("verify_migration_independent")

DEV = T.DEFAULT_DEVICE

print("=== ① --device 是否真说了算（把装置改成恒等，产出应不同）===")
d = tempfile.mkdtemp(prefix="rv56_")
orig = os.path.join(d, "orig.py"); shutil.copyfile(DEV, orig)
mut  = os.path.join(d, "mut.py");  shutil.copyfile(DEV, mut)
with open(mut, "a", encoding="utf-8") as fh:
    fh.write("\n\ndef neutralize(sql_text):\n    return sql_text\n")

for label, p in (("原件", orig), ("变异(恒等)", mut)):
    rc, out, err = T.dev_neutralize(p, "USE mysql;")
    print("  %-12s rc=%s 产出=%r" % (label, rc, out))

print("\n=== ② 净0 盲区：DROP + CREATE 同一个库 ⇒ 集合差分应『看不见』 ===")
T.reset_probe(True)
before = T.schemata()
print("  before 含探针库:", T.PROBE_DB in before)
new, gone = T.engine_dd_effect("DROP DATABASE `%s`; CREATE DATABASE `%s`;" % (T.PROBE_DB, T.PROBE_DB))
print("  引擎差分: 新增=%s 减少=%s" % (sorted(new), sorted(gone)))
print("  ⇒ 工具判『安全』(=无差集) ?", (not new and not gone), "  ★ 但该库<确被删过又重建>（数据已失）")
T.reset_probe(False)
print("  探针库残留:", [x for x in T.schemata() if x.startswith("qk_t56")])

print("\n=== ③ reset_probe 是否真 drop 了变体库（自陈 bug#2）===")
T.run_sql("CREATE DATABASE IF NOT EXISTS `%s2`;" % T.PROBE_DB)
print("  建 qk_t56_dd2 后:", [x for x in T.schemata() if x.startswith("qk_t56")])
T.reset_probe(True)
print("  reset_probe 后 :", [x for x in T.schemata() if x.startswith("qk_t56")])
T.reset_probe(False)
shutil.rmtree(d, ignore_errors=True)
