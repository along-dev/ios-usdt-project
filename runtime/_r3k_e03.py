# -*- coding: utf-8 -*-
"""让 3 个判据脚本的临时写入目录可被环境变量覆盖（E-03 的真正根因）。

★ 背景（审核 E 的 E-03）：
  这 3 个脚本【硬编码】把中间产物写到 `02-backend-node/.verify_tmp_storage*`
  与 `.rt_storage` ⇒ **污染产物目录**（实测 40 个文件）。
  上一轮我只在执行器里设置了 TMP/TEMP，但**脚本自身不看这些变量** ⇒ 未根除。

★ 改法（最小 + 零风险）：
  在这些常量定义处，改为【可用 DSH_VERIFY_TMP 覆盖】：
      const DSH_TMP = process.env.DSH_VERIFY_TMP || '';
      const ro = DSH_TMP ? path.join(DSH_TMP, '.verify_tmp_storage')
                         : path.join(ROOT, '02-backend-node', '.verify_tmp_storage');
  ★ 不设 DSH_VERIFY_TMP ⇒ **行为与原实现逐字等价**（默认路径不变）。

★ 本脚本【只改这 3 个文件】，且【保留原行于注释】以便回溯。
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import hashlib
import io
import os
import re

ROOT = IOS_ROOT + r"\_integration\_fix_work"

# (文件, 原行正则, 替换函数)
TARGETS = [
    ("verify_entries_coruna.mjs", [
        (r"const ro = path\.join\(ROOT, '02-backend-node', '\.verify_tmp_storage'\);",
         "const DSH_TMP = (process.env.DSH_VERIFY_TMP || '').trim();\n"
         "// ★ T26 收尾（E-03）：可被 DSH_VERIFY_TMP 覆盖；不设则保持原路径\n"
         "// ── 原行（留痕）：const ro = path.join(ROOT, '02-backend-node', '.verify_tmp_storage');\n"
         "const ro = DSH_TMP ? path.join(DSH_TMP, '.verify_tmp_storage')\n"
         "                   : path.join(ROOT, '02-backend-node', '.verify_tmp_storage');"),
        (r"const ro2 = path\.join\(ROOT, '02-backend-node', '\.verify_tmp_storage_ds'\);",
         "// ── 原行（留痕）：const ro2 = path.join(ROOT, '02-backend-node', '.verify_tmp_storage_ds');\n"
         "const ro2 = DSH_TMP ? path.join(DSH_TMP, '.verify_tmp_storage_ds')\n"
         "                    : path.join(ROOT, '02-backend-node', '.verify_tmp_storage_ds');"),
    ]),
    ("verify_i1c2_darksword_entries.mjs", [
        (r"const STORAGE = path\.join\(ROOT, '02-backend-node', '\.verify_tmp_storage_ds'\);",
         "const DSH_TMP = (process.env.DSH_VERIFY_TMP || '').trim();\n"
         "// ★ T26 收尾（E-03）：可被 DSH_VERIFY_TMP 覆盖；不设则保持原路径\n"
         "// ── 原行（留痕）：const STORAGE = path.join(ROOT, '02-backend-node', '.verify_tmp_storage_ds');\n"
         "const STORAGE = DSH_TMP ? path.join(DSH_TMP, '.verify_tmp_storage_ds')\n"
         "                        : path.join(ROOT, '02-backend-node', '.verify_tmp_storage_ds');"),
    ]),
    ("verify_i1c2_runtime.mjs", [
        (r"const r = await coruna\.syncCorunaPayloads\(path\.join\(TPL, 'coruna'\), path\.join\(ROOT, '02-backend-node', '\.rt_storage'\),",
         "const DSH_TMP = (process.env.DSH_VERIFY_TMP || '').trim();\n"
         "const RT_STORAGE = DSH_TMP ? path.join(DSH_TMP, '.rt_storage')\n"
         "                           : path.join(ROOT, '02-backend-node', '.rt_storage');\n"
         "// ── 原行（留痕）：… path.join(ROOT, '02-backend-node', '.rt_storage') …\n"
         "const r = await coruna.syncCorunaPayloads(path.join(TPL, 'coruna'), RT_STORAGE,"),
    ]),
]

for fname, subs in TARGETS:
    p = os.path.join(ROOT, fname)
    if not os.path.isfile(p):
        print("  [缺] %s" % fname)
        continue
    raw = open(p, "rb").read()
    before = hashlib.sha256(raw).hexdigest()
    s = raw.decode("utf-8")
    n = 0
    for pat, rep in subs:
        new_s, cnt = re.subn(pat, lambda m: rep, s, count=1)
        if cnt:
            s = new_s
            n += cnt
        else:
            print("    ★ 未匹配: %s" % pat[:60])
    out = s.encode("utf-8")
    open(p, "wb").write(out)
    after = hashlib.sha256(open(p, "rb").read()).hexdigest()
    print("  %-42s 替换 %d 处  %s→%s  (%d→%d B)"
          % (fname, n, before[:12], after[:12], len(raw), len(out)))
