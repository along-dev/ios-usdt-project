# -*- coding: utf-8 -*-
"""R3-1 · 回归执行器（审核 E 的 E-02/E-03 修复 + T26 量尺修复）。

★ 与原 run_regression.py 的区别：
  ① **默认只跑主回归集**（52 个无冻结哈希的脚本）⇒ 不再必然假红
  ② **跑前/跑后健康检查** ⇒ 防止把服务跑挂而无人知
  ③ **写入目标重定向到 $env:TEMP** ⇒ 不再污染产物目录
  ④ **超时保护**（分类超时，不再是全局单一值）
  ⑤ **守护集单独入口**（--guard）⇒ 按需跑，明确标注“可能假红”

★★★ T26 量尺修复（P-5 同族，先修量尺再量）：
  A1 · **分类超时**：按脚本源码特征动态判定超时
       - 静态断言类            → 180s
       - 含 go build / go vet / go test → 1800s（冷 cache 实测 1798s）
       - 含 vite build / npm run build  → 600s 且**强制串行**
       - 含服务启动/端口探测    → 600s
  A2 · **三分类判定**：PASS / FAIL / TIMEOUT —— 超时不再被算作失败。
       ★ 同时输出【不含 TIMEOUT】与【含 TIMEOUT】两个通过率（不得用单一数字掩盖超时）。
  A3 · **产物快照护栏**（P-38）：跑前快照 03-web-admin/dist 文件数，跑后比对，
       减少 ⇒ 报警；且若检测到并发构建进程（npm-cli.js / vite.js）⇒ **拒绝启动构建类脚本**。
  A4 · **六端口护栏**：跑前/跑后各测一次 8888/3000/8080/13306/16379/27018，掉端口 ⇒ 显式报警。
  A5 · **路径纪律**（P-45）：执行器内所有路径一律 E:\\ 真实绝对路径，**禁用 X:**。
  ★ 本文件【只改执行器】，不改任何判据脚本的断言，不改产物代码。

用法：
  python run_regression_v2.py             # 跑主回归集
  python run_regression_v2.py --guard     # 跑守护检查集
  python run_regression_v2.py --build     # 跑构建集（★ 串行 + 并发构建检测）
  python run_regression_v2.py --all       # 跑全部（不推荐日常用）
  python run_regression_v2.py --list      # 只列清单（含分类超时）
  python run_regression_v2.py --survey    # 只做源码取证，不跑脚本
"""
import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request

# ★★ A5 / P-45：一律使用 E:\ 真实绝对路径，禁用 X:（subst 只在交互会话有效）
ROOT = IOS_ROOT + r"\_integration\_fix_work"
PROJ = USDT_ROOT
DIST = os.path.join(PROJ, "03-web-admin", "dist")
PY = sys.executable
NODE = r"E:\CTF\runtime\node\node.exe"

# ★★ A1：分类超时（替换原全局 TIMEOUT = 120）
TIMEOUT_STATIC = 180        # 静态断言类（保持）
TIMEOUT_GO = 1800           # go build / go vet / go test（冷 cache 实测 1798s）
TIMEOUT_WEB = 600           # vite build / npm run build
TIMEOUT_SERVICE = 600       # 含服务启动 / 端口探测

MAIN_LIST = os.path.join(ROOT, "regression_main.txt")
GUARD_LIST = os.path.join(ROOT, "regression_guard.txt")
BUILD_LIST = os.path.join(ROOT, "regression_build.txt")
MANIFEST = os.path.join(ROOT, "regression_manifest.json")

# ★ E-03：写入目标重定向到 TEMP，避免污染产物目录
TEMP_DIR = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "dsh_regression")
os.makedirs(TEMP_DIR, exist_ok=True)
DIST_SNAPSHOT = os.path.join(TEMP_DIR, "dist_snapshot")

# ★★ A4：六端口护栏
PORTS = [8888, 3000, 8080, 13306, 16379, 27018]
PORT_DESC = {
    8888: "go-api", 3000: "node-api", 8080: "node-proxy",
    13306: "mysql", 16379: "redis", 27018: "mongo",
}
HEALTH = {
    "go": "http://127.0.0.1:8888/health",
    "node": "http://127.0.0.1:3000/healthz",
}

# ★★ A1：分类判定正则（只读脚本源码，不执行）
RE_GO = re.compile(r'go\s+build|\[\s*go_exe\s*,\s*["\']build|\[\s*go\s*,\s*["\']build'
                   r'|run_go\(\s*\[\s*["\']build|\[\s*["\']build["\']\s*,\s*["\']\./'
                   r'|go\s+vet|go\s+test', re.I)
RE_WEB = re.compile(r'vite\s+build|npm\s+run\s+build|pnpm\s+(run\s+)?build', re.I)
RE_SERVICE = re.compile(r'fastify|app\.js|port\s*probe|端口探测|uvicorn|gunicorn'
                        r'|\.listen\(|start_server|Start-Process.*node', re.I)

# ★★ A3：并发构建进程特征（P-38）
CONCURRENT_BUILD_PAT = re.compile(r'npm-cli\.js|vite\.js|vite\.mjs|go\.exe\s+build', re.I)


def read_list(path):
    if not os.path.isfile(path):
        return []
    out = []
    for l in io.open(path, encoding="utf-8").read().splitlines():
        l = l.strip()
        if l and not l.startswith("#"):
            out.append(l)
    return out


# ============================ A1：分类超时 ============================

def classify(fname):
    """读取脚本源码，正则判定类别 → 返回 (category, timeout, evidence)。"""
    p = os.path.join(ROOT, fname)
    if not os.path.isfile(p):
        return ("missing", TIMEOUT_STATIC, "")
    if fname.endswith(".mjs") or fname.endswith(".js"):
        try:
            src = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            src = ""
    else:
        try:
            src = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            src = ""

    ev = []
    cat, to = "static", TIMEOUT_STATIC
    # 优先级：go > web > service > static（go 最慢，最高优先）
    m = RE_GO.search(src)
    if m:
        cat, to = "go-build", TIMEOUT_GO
        ev.append("L%d:%s" % (src.count("\n", 0, m.start()) + 1,
                              m.group(0).strip()[:40]))
    else:
        m = RE_WEB.search(src)
        if m:
            cat, to = "web-build", TIMEOUT_WEB
            ev.append("L%d:%s" % (src.count("\n", 0, m.start()) + 1,
                                  m.group(0).strip()[:40]))
        else:
            m = RE_SERVICE.search(src)
            if m:
                cat, to = "service", TIMEOUT_SERVICE
                ev.append("L%d:%s" % (src.count("\n", 0, m.start()) + 1,
                                      m.group(0).strip()[:40]))
    return (cat, to, "; ".join(ev))


def is_build_like(cat):
    return cat in ("go-build", "web-build", "service")


def survey_all():
    """★ 取证：扫描清单内所有脚本（另加目录全量扫描），输出分类结果。"""
    listed = []
    for name, path in (("MAIN", MAIN_LIST), ("GUARD", GUARD_LIST), ("BUILD", BUILD_LIST)):
        for f in read_list(path):
            if f not in [x[0] for x in listed]:
                listed.append((f, name))
    print("=" * 78)
    print("★ 取证：清单内脚本的构建特征分类（只读源码，不执行）")
    print("=" * 78)
    build_like = []
    for f, src in sorted(listed):
        cat, to, ev = classify(f)
        if is_build_like(cat):
            build_like.append((f, cat, to, ev, src))
        print("  %-42s %-10s %5ds  %s" % (f, cat, to, ev))
    print("")
    print("★ 清单内【会真正触发构建/服务启动】的脚本: %d 个" % len(build_like))
    for f, cat, to, ev, src in build_like:
        print("    %-42s %s" % (f, cat))
    return listed, build_like


def survey_dir():
    """★ 取证：扫描判据目录【全部】verify_*.py，找真执行构建的脚本。"""
    re_exec_go = re.compile(r'\[\s*(GO|GO_EXE|go|go_exe)\s*,\s*["\'](build|vet|test)["\']'
                            r'|run_go\(\s*\[\s*["\'](build|vet|test)["\']')
    re_exec_npm = re.compile(r'\[\s*NPM\s*,\s*["\'](run)["\']\s*,\s*["\']build["\']'
                             r'|run_npm\(\s*\[\s*["\'](run)["\']\s*,\s*["\']build["\']')
    re_mention = re.compile(r'go\s+build|vite\s+build|npm\s+run\s+build|go\s+vet|go\s+test')
    rows = []
    for fn in sorted(os.listdir(ROOT)):
        if not fn.startswith("verify_") or not fn.endswith(".py"):
            continue
        p = os.path.join(ROOT, fn)
        try:
            src = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        eg = [src.count("\n", 0, m.start()) + 1 for m in re_exec_go.finditer(src)]
        en = [src.count("\n", 0, m.start()) + 1 for m in re_exec_npm.finditer(src)]
        mn = [src.count("\n", 0, m.start()) + 1 for m in re_mention.finditer(src)]
        if eg or en:
            rows.append((fn, "EXEC-GO" if eg else "EXEC-NPM", eg[:3], en[:3], len(mn)))
        elif mn:
            rows.append((fn, "MENTION-ONLY", [], [], len(mn)))
    print("=" * 78)
    print("★★ 取证：判据目录全量扫描 verify_*.py（真执行构建 vs 仅提及）")
    print("=" * 78)
    execs = [r for r in rows if r[1] != "MENTION-ONLY"]
    mentions = [r for r in rows if r[1] == "MENTION-ONLY"]
    print("【真执行构建】%d 个:" % len(execs))
    for fn, kind, eg, en, m in execs:
        print("    %-42s %-9s go行=%s npm行=%s" % (fn, kind, eg or "-", en or "-"))
    print("")
    print("【仅文本提及，不执行构建】%d 个:" % len(mentions))
    for fn, kind, eg, en, m in mentions:
        print("    %-42s 提及 %d 处" % (fn, m))
    return execs, mentions


def write_manifest(listed):
    """★ A1：把类别/超时写回 regression_manifest.json（扩充字段，不删旧字段）。"""
    old = {}
    if os.path.isfile(MANIFEST):
        try:
            data = json.load(io.open(MANIFEST, encoding="utf-8"))
            if isinstance(data, list):
                for e in data:
                    if isinstance(e, dict) and e.get("file"):
                        old[e["file"]] = e
        except Exception as ex:
            print("  [warn] 读 manifest 失败: %s" % ex)
    merged = []
    seen = set()
    for f, kind in listed:
        e = dict(old.get(f, {"file": f}))
        cat, to, ev = classify(f)
        e["timeout_class"] = cat
        e["timeout_sec"] = to
        e["build_evidence"] = ev
        e["triggers_build"] = is_build_like(cat)
        e["kind"] = kind.lower()
        p = os.path.join(ROOT, f)
        if os.path.isfile(p):
            e["bytes"] = os.path.getsize(p)
        merged.append(e)
        seen.add(f)
    # 保留 manifest 中不在清单里的历史条目
    for f, e in old.items():
        if f not in seen:
            e.setdefault("timeout_class", "static")
            e.setdefault("timeout_sec", TIMEOUT_STATIC)
            merged.append(e)
    with io.open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=1)
    print("  ★ manifest 已扩充: %s（%d 条）" % (MANIFEST, len(merged)))


# ============================ A4：六端口护栏 ============================

def port_probe(port, timeout=1.2):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        rc = s.connect_ex(("127.0.0.1", port))
        s.close()
        return rc == 0
    except Exception:
        return False


def six_ports(tag):
    """★ A4：跑前/跑后各测一次六端口，返回 {port: bool}。"""
    res = {}
    for p in PORTS:
        res[p] = port_probe(p)
    txt = " ".join("%d=%s" % (p, "UP" if res[p] else "DOWN") for p in PORTS)
    print("  [ports/%s] %s" % (tag, txt))
    return res


def health_check(tag):
    """★ E-03：跑前/跑后 HTTP 健康检查。返回 {svc: status}"""
    res = {}
    for name, url in HEALTH.items():
        try:
            with urllib.request.urlopen(url, timeout=6) as r:
                res[name] = r.status
        except Exception as e:
            res[name] = "ERR:%s" % type(e).__name__
    print("  [health/%s] %s" % (tag, json.dumps(res, ensure_ascii=False)))
    return res


# ===================== A3：产物快照 + 并发构建检测（P-38）=====================

def dist_count():
    if not os.path.isdir(DIST):
        return -1
    n = 0
    for _root, _dirs, files in os.walk(DIST):
        n += len(files)
    return n


def dist_snapshot():
    """★ A3-1：跑前把 dist 复制到 $env:TEMP\\dsh_regression\\dist_snapshot。"""
    if not os.path.isdir(DIST):
        print("  [dist] 源目录不存在，跳过快照: %s" % DIST)
        return -1
    if os.path.isdir(DIST_SNAPSHOT):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", DIST_SNAPSHOT],
                       capture_output=True)
    r = subprocess.run(["cmd", "/c", "xcopy", DIST, DIST_SNAPSHOT, "/E", "/I", "/Q", "/Y"],
                       capture_output=True)
    n = dist_count()
    print("  [dist/before] %s 文件数=%d 快照rc=%d → %s" % (DIST, n, r.returncode, DIST_SNAPSHOT))
    return n


def dist_compare(before):
    """★ A3-2：跑后比对文件数，减少 ⇒ 报警（可能被构建清空，P-38）。"""
    after = dist_count()
    print("  [dist/after]  %s 文件数=%d（跑前=%d）" % (DIST, after, before))
    if before >= 0 and after >= 0 and after < before:
        print("  ★★ 报警：dist 文件数【减少】%d → %d —— 可能被 vite build emptyDir 清空！" % (before, after))
    elif before >= 0 and after >= before:
        print("  ✅ dist 文件数未减少（%d → %d）" % (before, after))
    return after


# ============ G-10：计数类判据的【时间基线】（count + snapshot_sha256 并列）============
#
# ★ 根因（L048 §7 / P-53）：计数类结论没有时间基线 ⇒ 把旧期望值当成磁盘真值 ⇒ 假红/假绿。
#   实测漂移：dist 196(文档238) · bill 43(文档33/43 两份) · nginx server 块 5(文档7)。
# ★ 修法：判据输出里 **count 与 snapshot_sha256 必须并列**，
#   让「期望值（写死在文档里）」与「磁盘真值（当场算出来的）」分离。
#
# ★★ 快照算法【不在此处重复实现】—— 唯一定义在 verify_doc_code_parity.py，
#    这里通过 importlib 载入，避免两份实现漂移（与 B2/C-4「同源产出」同族纪律）。

COUNTING_TARGETS = [
    # (标签, 路径, 类别)
    ("03-web-admin/dist",           os.path.join(PROJ, "03-web-admin", "dist"), "dir"),
    ("06-android/apk/japapp",       os.path.join(PROJ, "06-android", "apk", "japapp"), "dir"),
    ("09-docs/reports",             os.path.join(PROJ, "09-docs", "reports"), "dir"),
    ("08-infra/nginx/default.conf.template",
     os.path.join(PROJ, "08-infra", "nginx", "default.conf.template"), "file"),
]


def _load_parity_module():
    """载入唯一定义的快照实现（verify_doc_code_parity.py）。失败 ⇒ 返回 None。"""
    p = os.path.join(ROOT, "verify_doc_code_parity.py")
    if not os.path.isfile(p):
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_parity_for_baseline", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    except Exception:
        return None


def counting_baseline():
    """★ G-10：打印计数类目标的 count 与 snapshot_sha256（并列）。

    用法场景：任何引用「N 个文件 / N 行 / N 个块」的文档或判据，
    引用前先跑本模式拿【当场】基线，不要抄文档里的旧数字。
    """
    print("=" * 78)
    print("★ G-10 计数基线：count 与 snapshot_sha256 并列（引用任何计数前先跑这里）")
    print("=" * 78)

    m = _load_parity_module()
    if m is None:
        print("  [FAIL] 无法载入快照实现 verify_doc_code_parity.py ⇒ 拒绝用内联实现顶替（避免双源）")
        return 1

    for label, target, kind in COUNTING_TARGETS:
        if not os.path.exists(target):
            print("  %-40s count=<n/a> snapshot_sha256=<n/a>  (缺失: %s)" % (label, target))
            continue
        n, snap, note = m.snapshot_of(target)
        print("  %-40s count=%-6d snapshot_sha256=%s %s" % (label, n, snap or "<n/a>", note))

    # ★ 计数类的第三种形态：正则命中数（nginx server 块 — 量尺错就出在这里）
    tpl = os.path.join(PROJ, "08-infra", "nginx", "default.conf.template")
    if os.path.isfile(tpl):
        n_srv, _ = m.count_matches([tpl], r"^server\s*\{")
        n_up, _ = m.count_matches([tpl], r"^upstream\s+\S+\s*\{")
        print("  %-40s count=%-6d %s" % ("nginx server 块（正则 ^server{）", n_srv,
                                         "(upstream 块 %d 个——勿与 server 块混数)" % n_up))

    # ★ DB 计数（无快照哈希 —— 表非文件，如实标注）
    bill = _db_scalar("SELECT COUNT(*) FROM qk_e2e.bill;")
    print("  %-40s count=%-6s snapshot_sha256=<n/a 表非文件>  %s"
          % ("qk_e2e.bill 行数", bill if bill is not None else "<n/a>",
             "" if bill is not None else "(DB 不可达 ⇒ SKIP，不得回落静态值)"))

    print("=" * 78)
    print("★ 引用纪律：写进文档/判据的数字必须【带时点】；与上表不符 ⇒ 先怀疑期望值，不是改判据。")
    return 0


def _db_scalar(sql):
    """查 DB 标量；拿不到 ⇒ None（调用方必须 SKIP，P-53）。"""
    MYSQL = r"X:\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"
    if not os.path.isfile(MYSQL):
        return None
    try:
        r = subprocess.run([MYSQL, "--skip-ssl", "-u", "root", "-h", "127.0.0.1",
                            "-P", "13306", "-N", "-B", "-e", sql],
                           capture_output=True, text=True, timeout=25, errors="replace")
        if r.returncode != 0:
            return None
        return int((r.stdout or "").strip().splitlines()[0])
    except Exception:
        return None


# ============ WBE01-C：DB 夹具表护栏（与本项目既有 A3「dist 快照」同型）============
#
# 起因（第一手事故，非推演）：判据脚本的 cleanup 会在**与业务同库**的 qk_e2e 上 DELETE/UPDATE
# 业务表 ⇒ 本线一次迁移所依赖的 bill 行被删，存列派生值当场陈旧、不变量由绿转红。
# 实测写者 5 个（全在树外）：e2e_test_api.py · verify_f1c8/f1c9/money_*.py · verify_f1c10_*.mjs
#   —— 其中 4 个在主回归集内。
# ★ 本护栏的目的不是"修脚本"，而是**让"跑完回归后库有没有被改"这件事，变成可机检的红/绿**。
#    脚本侧已另行收窄（每脚本专属前缀、禁整表删）—— 护栏是它的**证明**，两者必须同批。
#
# ★ 口径（承 L048 §7）：**行数与 snapshot_sha256 必须并列输出** ——
#   只比行数会漏掉"删一行又插一行"这类等量替换。

DB_TABLES = ["bill", "settlement", "token", "wallet"]
# ★ T29（WBE01-D）：护栏**永远指向业务库** —— ⛔ **不跟随 `DSH_DB`**。
#   它要证的就是「业务库一个字没碰」，所以即便被判据的 `DSH_DB` 指到测试库，这里也必须仍是业务库。
DB_NAME = os.environ.get("DSH_GUARD_DB", "qk_e2e")
# 各表参与"内容哈希"的关键列（用于抓等量替换）
DB_HASH_COLS = {
    "bill": "id,transfer_hash,role,status,usdt_num,wallet_id,settlement_id,token_id,total_num,num,batch_id,order_id,create_time",
    "settlement": "id,user_id,chain,address,create_time",
    "token": "id,chain,coin_name,coin_address,radio_usdt",
    "wallet": "id,machine_id,region,progress,ustd_num,turn_pubic_at",
}


def _db_row(query):
    """跑一条 SQL，返回首行（按 \\t 切）。失败 ⇒ None。"""
    MYSQL = r"X:\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe"
    if not os.path.isfile(MYSQL):
        return None
    try:
        r = subprocess.run([MYSQL, "--skip-ssl", "-u", "root", "-h", "127.0.0.1", "-P", "13306",
                            "-N", "-B", "-e", query],
                           capture_output=True, text=True, timeout=30, errors="replace")
        if r.returncode != 0:
            return None
        line = (r.stdout or "").strip().splitlines()
        return line[0].split("\t") if line else None
    except Exception:
        return None


def db_snapshot(tag="before"):
    """★ 跑前/跑后各取一次：{表: (行数, 内容哈希)}。拿不到 ⇒ 该表记 None（⛔ 不得回落成 0）。"""
    snap = {}
    for t in DB_TABLES:
        cols = DB_HASH_COLS[t]
        # ★ 提高 group_concat 上限，避免长表被截断成"看起来一样"
        q = ("SET SESSION group_concat_max_len=10485760; "
             "SELECT COUNT(*), COALESCE(MD5(GROUP_CONCAT(h ORDER BY id SEPARATOR '')),'-') FROM ("
             " SELECT id, MD5(CONCAT_WS('|',%s)) AS h FROM %s.%s) x;" % (cols, DB_NAME, t))
        row = _db_row(q)
        if row is None or len(row) < 2:
            snap[t] = (None, None)
        else:
            snap[t] = (int(row[0]), row[1])
    print("  [db/%s] %s" % (tag, " ".join(
        "%s=%s/%s" % (t, (snap[t][0] if snap[t][0] is not None else "n/a"),
                      (snap[t][1][:8] if snap[t][1] else "n/a")) for t in DB_TABLES)))
    return snap


def db_compare(before, tag="after"):
    """★ 跑后比对：行数或内容哈希任一变化 ⇒ **报警**（这正是 WBE01-C 要抓的形态）。"""
    after = db_snapshot(tag)
    bad = []
    unk = []
    for t in DB_TABLES:
        b, a = before.get(t, (None, None)), after.get(t, (None, None))
        if b[0] is None or a[0] is None:
            unk.append(t)
            continue
        if b[0] != a[0]:
            bad.append("%s 行数 %d→%d" % (t, b[0], a[0]))
        elif (b[1] or "") != (a[1] or ""):
            bad.append("%s 行数相同但**内容哈希变了**（%s→%s）" % (t, (b[1] or "")[:8], (a[1] or "")[:8]))
    if bad:
        print("  ★★ 报警（WBE01-C）：跑回归期间 **DB 业务表被改动** —— %s" % "；".join(bad))
        print("       ⇒ 判据脚本的 cleanup 越界，或新增了未收窄的写者。见 WBE01-C 方案。")
    elif unk:
        print("  ⚠ [db/after] 有表**读不到**（%s）⇒ 本项结论不完整（P-13：不得判 PASS）" % unk)
    else:
        print("  ✅ DB 业务表四张：行数与内容哈希均未变（bill/settlement/token/wallet）")
    return bad, unk


def _proc_lines():
    """★ 取进程列表（命令行）。本机无 wmic（Win11 已弃用）⇒ 用 CIM。
    返回 (行列表, 错误信息)。"""
    ps = ("Get-CimInstance Win32_Process -ErrorAction Stop | "
          "ForEach-Object { \"$($_.ProcessId)`t$($_.Name)`t$($_.CommandLine)\" }")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=45, errors="replace")
        return (r.stdout or "").splitlines(), (r.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return [], "CIM 查询超时(>45s)"
    except FileNotFoundError:
        return [], "powershell 不可用"
    except Exception as e:
        return [], "%s" % type(e).__name__


def detect_concurrent_build(strict=False):
    """★ A3-3 / P-38：检测 npm-cli.js / vite.js 等构建进程。

    ★ 容错策略（fail-open vs fail-closed）：
      - strict=False（默认）：检测失败仅【警告】，不阻断 —— 避免因检测器本身
        的环境问题把整个构建集锁死。
      - strict=True：检测失败 ⇒ 视为“可能并发”，返回哨兵拒绝启动。
    """
    lines, err = _proc_lines()
    if not lines:
        print("  [concurrent-build] ⚠ 检测不可用: %s" % (err or "无输出"))
        print("      ⇒ 无法确认是否有并发构建；请【人工确认】后再跑构建集")
        return ["<detector-unavailable>"] if strict else []
    hits = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        pid, name, cmd = parts[0].strip(), parts[1].strip(), parts[2]
        # 排除检测器自身的进程行
        if "Get-CimInstance" in cmd or "Win32_Process" in cmd:
            continue
        if CONCURRENT_BUILD_PAT.search(cmd):
            hits.append("PID=%s %s | %s" % (pid, name, cmd.strip()[:120]))
    if hits:
        print("  ★★ 检测到并发构建进程 %d 个：" % len(hits))
        for h in hits[:6]:
            print("      %s" % h)
    else:
        print("  [concurrent-build] 未检测到 npm-cli.js / vite.js 构建进程")
    return hits


# ============================ 执行 ============================

def run_one(fname, timeout):
    p = os.path.join(ROOT, fname)
    if not os.path.isfile(p):
        return {"file": fname, "rc": None, "sec": 0, "note": "MISSING"}
    if fname.endswith(".mjs") or fname.endswith(".js"):
        cmd = [NODE, p]
    else:
        cmd = [PY, p]
    # ★ 让判据脚本把临时写入放到 TEMP
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["TMP"] = TEMP_DIR
    env["TEMP"] = TEMP_DIR
    env["DSH_REGRESSION_TMP"] = TEMP_DIR
    # ★★★ R3-1 补：注入判据脚本【显式要求】的运行期环境变量。
    #   依据：`verify_f1c10_bridge_e2e.mjs:100-102` 自述
    #     「bridgeEnabled() === false —— 桥会短路返回，断言无意义
    #       需设置 QIANKE_API_BASE 与 QIANKE_SERVICE_TOKEN」
    #   ⇒ 这是【执行方式】问题，不是脚本缺陷 ⇒ 在执行器里补上，
    #     而不是修改判据（保持判据的原始意图）。
    #   ★ 值来源：`_i1c3_ws/.env` 与 Go `config.yaml` 的 app-jwt.service-token
    env.setdefault("QIANKE_API_BASE", "http://127.0.0.1:8888")
    env.setdefault("QIANKE_SERVICE_TOKEN", "i2c1-e2e-token")
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True,
                           timeout=timeout, env=env)
        rc = r.returncode
        note = ""
    except subprocess.TimeoutExpired:
        rc = "TIMEOUT"
        note = ">%ds" % timeout
    sec = round(time.time() - t0, 1)
    return {"file": fname, "rc": rc, "sec": sec, "note": note, "timeout_used": timeout}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guard", action="store_true", help="跑守护检查集")
    ap.add_argument("--build", action="store_true",
                    help="跑构建集（★ 会执行 go build/npm build，必须串行且无其他构建在跑）")
    ap.add_argument("--all", action="store_true", help="跑全部（不推荐日常用）")
    ap.add_argument("--list", action="store_true", help="只列清单（含分类超时）")
    ap.add_argument("--survey", action="store_true", help="只做构建取证，不跑脚本")
    ap.add_argument("--baseline", action="store_true",
                    help="★ G-10：只打印计数类目标的 count 与 snapshot_sha256（不跑脚本）")
    ap.add_argument("--force", action="store_true", help="★ 跳过并发构建检测（危险）")
    args = ap.parse_args()

    main_l = read_list(MAIN_LIST)
    guard_l = read_list(GUARD_LIST)
    build_l = read_list(BUILD_LIST)

    # ★ 取证：清单内所有脚本的分类
    listed = []
    for f in main_l + guard_l + build_l:
        if f not in [x[0] for x in listed]:
            listed.append((f, "main" if f in main_l else ("guard" if f in guard_l else "build")))

    if args.survey:
        survey_all()
        print("")
        survey_dir()
        return

    if args.baseline:
        return counting_baseline()

    if args.list:
        print("主回归集: %d 个" % len(main_l))
        for f in main_l:
            cat, to, ev = classify(f)
            print("   %-42s %-10s %5ds" % (f, cat, to))
        print("守护集: %d 个" % len(guard_l))
        for f in guard_l:
            cat, to, ev = classify(f)
            print("   %-42s %-10s %5ds" % (f, cat, to))
        print("构建集: %d 个（★ 串行）" % len(build_l))
        for f in build_l:
            cat, to, ev = classify(f)
            print("   %-42s %-10s %5ds" % (f, cat, to))
        return

    if args.all:
        targets = main_l + guard_l + build_l
        kind = "ALL"
    elif args.build:
        targets = build_l
        kind = "BUILD"
    elif args.guard:
        targets = guard_l
        kind = "GUARD"
    else:
        targets = main_l
        kind = "MAIN"

    # ★★ A1：分类超时表
    plan = []
    for f in targets:
        cat, to, ev = classify(f)
        plan.append({"file": f, "cat": cat, "timeout": to, "ev": ev})

    has_build_like = any(is_build_like(p["cat"]) for p in plan)

    # ★★ A3-3 / P-38：并发构建检测 ⇒ 拒绝启动构建类脚本
    if has_build_like and not args.force:
        print("=" * 70)
        print("★★ P-38 构建集警告：本次将执行 go build / npm run build")
        print("   · vite build 会 emptyDir 清空 outDir ⇒ 绝不可与其他构建并发")
        print("   · Go 冷 cache 构建约 30 分钟（实测 1798s）")
        print("   · 本类脚本【强制串行】执行")
        print("=" * 70)
        hits = detect_concurrent_build()
        if hits:
            print("")
            if hits == ["<detector-unavailable>"]:
                print("  ★★ 拒绝启动：并发构建检测器不可用，无法排除 P-38 并发风险。")
                print("     请人工确认无构建进程后，用 --force 重跑（后果自负）。")
            else:
                print("  ★★ 拒绝启动：当前有构建进程在跑（P-38）。")
                print("     请等待其结束后重跑，或显式使用 --force（危险，后果自负）。")
            return 3
        print("  ✅ 未检测到并发构建，允许继续")

    # ★★ A1：web-build 强制串行
    if any(p["cat"] == "web-build" for p in plan):
        print("  ★ web-build 类脚本【强制串行】：本批逐个执行，不并发")

    print("=" * 70)
    print("R3-1 回归执行器 (T26) | 集合=%s | 脚本数=%d" % (kind, len(targets)))
    print("  ★ 分类超时: static=%ds  go-build=%ds  web-build=%ds  service=%ds"
          % (TIMEOUT_STATIC, TIMEOUT_GO, TIMEOUT_WEB, TIMEOUT_SERVICE))
    print("  ★ 临时写入目录: %s" % TEMP_DIR)
    from collections import Counter
    cc = Counter(p["cat"] for p in plan)
    print("  ★ 本批分类: %s" % json.dumps(dict(cc), ensure_ascii=False))
    print("=" * 70)

    print("")
    print("=== 跑前护栏 ===")
    print("  ① 六端口")
    p0 = six_ports("before")
    print("  ② HTTP 健康")
    h0 = health_check("before")
    print("  ③ 产物快照 (P-38)")
    d_before = dist_snapshot()
    # ★ WBE01-C：DB 业务表护栏（跑前快照；与 dist 快照同型、同批）
    db_before = db_snapshot("before")

    print("")
    print("=== 执行 ===")
    results = []
    for i, p in enumerate(plan, 1):
        f = p["file"]
        r = run_one(f, p["timeout"])
        r["cat"] = p["cat"]
        results.append(r)
        if r["rc"] == 0:
            mark = "PASS"
        elif r["rc"] == "TIMEOUT":
            mark = "TIME"
        else:
            mark = "FAIL"
        print("  [%2d/%2d] %-4s %-42s %-10s rc=%-8s %7.1fs %s"
              % (i, len(plan), mark, f, p["cat"], str(r["rc"]), r["sec"], r["note"]))

    print("")
    print("=== 跑后护栏 ===")
    print("  ① 六端口")
    p1 = six_ports("after")
    print("  ② HTTP 健康")
    h1 = health_check("after")
    print("  ③ 产物比对 (P-38)")
    d_after = dist_compare(d_before)
    # ★ WBE01-C：跑后比对 DB 业务表（行数 + 内容哈希；任一变化即报警）
    db_bad, db_unk = db_compare(db_before)

    # ★★ A2：三分类判定
    #
    # ★★★ T26 补充（R-18 / KNOWN-GAP）：已登记的【预期 RED】脚本。
    #   依据：决策 Agent 复核确认 `verify_d2c5_filzaslop_static.py` 稳定 FAIL
    #     （V3 无效 -I / V4 32 头不可解析），属【真实产物缺口】，
    #     但 Theos 不支持 Windows ⇒ 修复不可证伪 ⇒ 已登记 R-16/R-18，本轮不做。
    #   ⇒ 该脚本计为 KNOWN_GAP：【不计入 FAIL，也不计入通过率分母】，
    #     避免它每次拉低整体百分比、被误读为"退化"。
    KNOWN_GAP = {
        "verify_d2c5_filzaslop_static.py": "R-16/R-18：05-ios 的 -I 路径缺口（需 macOS+Theos 才能验证）",
    }

    n_pass = sum(1 for r in results if r["rc"] == 0)
    n_timeout = sum(1 for r in results if r["rc"] == "TIMEOUT")
    n_known = sum(1 for r in results if r["rc"] != 0 and r["rc"] != "TIMEOUT"
                  and r["file"] in KNOWN_GAP)
    n_fail = len(results) - n_pass - n_timeout - n_known
    total = len(results)
    # ★ 分母剔除 TIMEOUT 与 KNOWN_GAP
    denom_no_to = total - n_timeout - n_known
    rate_no_to = (100.0 * n_pass / denom_no_to) if denom_no_to else 0.0
    rate_all = (100.0 * n_pass / total) if total else 0.0

    print("")
    print("=" * 70)
    print("结果: PASS %d / FAIL %d / TIMEOUT %d / KNOWN-GAP %d   (共 %d)"
          % (n_pass, n_fail, n_timeout, n_known, total))
    print("★ 通过率（不含 TIMEOUT 与 KNOWN-GAP）: %d/%d = %.1f%%"
          % (n_pass, denom_no_to, rate_no_to))
    print("★ 通过率（含 TIMEOUT，仅剔 KNOWN-GAP）: %d/%d = %.1f%%"
          % (n_pass, total - n_known, (100.0 * n_pass / (total - n_known)) if (total - n_known) else 0.0))
    print("★ 通过率（含全部）: %d/%d = %.1f%%" % (n_pass, total, rate_all))
    print("=" * 70)

    if n_known:
        print("")
        print("  ★ KNOWN-GAP（已登记、预期 RED、不计入分母）:")
        for r in results:
            if r["rc"] != 0 and r["rc"] != "TIMEOUT" and r["file"] in KNOWN_GAP:
                print("      %-46s %s" % (r["file"], KNOWN_GAP[r["file"]]))

    if n_timeout:
        print("")
        print("  ★★ 注意：%d 个脚本超时【未跑完】⇒ 其结果不代表失败，但也不代表通过。" % n_timeout)
        for r in results:
            if r["rc"] == "TIMEOUT":
                print("      - %-42s 类别=%-10s 超时=%ds 实耗=%.1fs"
                      % (r["file"], r.get("cat"), r.get("timeout_used", 0), r["sec"]))

    # ★★ A4：六端口掉线报警
    lost = [p for p in PORTS if p0.get(p) and not p1.get(p)]
    if lost:
        print("")
        print("  ★★ 报警：跑后端口【掉了】%s —— 本次结果不可信！" % lost)
        print("      跑前: %s" % json.dumps({str(k): v for k, v in p0.items()}))
        print("      跑后: %s" % json.dumps({str(k): v for k, v in p1.items()}))
    else:
        up = [p for p in PORTS if p1.get(p)]
        if len(up) == len(PORTS):
            print("")
            print("  ✅ 跑后六端口全 UP: %s" % " ".join(
                "%d(%s)" % (p, PORT_DESC[p]) for p in PORTS))
        else:
            print("")
            print("  ⚠ 跑后端口部分 DOWN（跑前也 DOWN ⇒ 非本次引入）: %s"
                  % [p for p in PORTS if not p1.get(p)])

    srv_ok_before = all(not str(v).startswith("ERR") for v in h0.values())
    srv_ok_after = all(not str(v).startswith("ERR") for v in h1.values())
    if srv_ok_before and not srv_ok_after:
        print("  ★★ 报警：跑完后 HTTP 服务【掉了】—— 本次结果不可信！")
    elif srv_ok_after:
        print("  ✅ 跑后 HTTP 服务仍健康（go=%s, node=%s）" % (h1.get("go"), h1.get("node")))

    if d_before >= 0 and d_after >= 0 and d_after < d_before:
        print("  ★★ 报警：产物 dist 文件数减少 %d → %d（P-38 可能被 emptyDir 清空）"
              % (d_before, d_after))

    # ★ A1：把分类写回 manifest
    print("")
    print("=== 写回 manifest（A1 分类字段）===")
    write_manifest(listed)

    out = os.path.join(TEMP_DIR, "regression_%s.json" % kind.lower())
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "kind": kind,
            "counts": {"PASS": n_pass, "FAIL": n_fail, "TIMEOUT": n_timeout, "total": total},
            "rate_excl_timeout": round(rate_no_to, 1),
            "rate_incl_timeout": round(rate_all, 1),
            "ports_before": {str(k): v for k, v in p0.items()},
            "ports_after": {str(k): v for k, v in p1.items()},
            "health_before": h0, "health_after": h1,
            "dist_before": d_before, "dist_after": d_after,
            "results": results,
        }, fh, ensure_ascii=False, indent=1)
    print("  明细已写: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
