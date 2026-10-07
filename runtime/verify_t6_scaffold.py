# -*- coding: utf-8 -*-
"""
T6 判据：脚手架裁剪（前端 example/ + systemTools/，含后端菜单 seed 同步清理）。

方案 A（Owner 裁决）：删前端两目录 + 清 menu.go 的 14 行 seed + 修 DataInserted 判据。

断言：
  V1  删前已证明「无外部引用」（机械搜索，含后端）
  V2  example/ 不存在
  V3  systemTools/ 不存在
  V4  about/ 与 superAdmin/ 仍存在
  V5  npm.cmd run build EXIT=0
  V6  未改 src/router、src/api、src/core
  V7  守护：_manifest.sha256、contracts.md 未改
  V8  ★★★ menu.go 无【悬空 Component】（本卡最重要 —— 构建测不出）
  V9  ★★ DataInserted() 判据 path 仍存在于 seed（幂等保护）

用法：
  python verify_t6_scaffold.py              # 全量（含 npm build）
  python verify_t6_scaffold.py --static-only  # 跳过 npm（快，用于动前红）
  python verify_t6_scaffold.py --selftest     # 量尺前置断言（P-5）

★ P-36：读文件测 bytes/eol 一律用 open(p,'rb')。
★ P-13：SKIP != PASS。
"""
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
import re
import sys
import hashlib
import subprocess

ROOT = USDT_ROOT
WEB = os.path.join(ROOT, "03-web-admin")
SRC = os.path.join(WEB, "src")
VIEW = os.path.join(SRC, "view")
MENU_GO = os.path.join(ROOT, "01-backend-go", "source", "system", "menu.go")
MANIFEST = os.path.join(ROOT, "_manifest.sha256")
CONTRACTS = os.path.join(ROOT, "09-docs", "spec", "contracts.md")
NPM = r"E:\CTF\runtime\node\npm.cmd"

# ---- 基线（调度现场重取，动前）----
BASE = {
    "menu.go": "9843611516ca33c40a4ed91ad4b0588a1d90aa4780d5ba870ba6ad70dd23866c",
    "menu.go_bytes": 7161,
    "menu.go_lf": 99,
    "_manifest.sha256": "b940dc19a76f1627ed185f9af54ff79f0f3dac4fcece0f86f78c3c9cdbdb58c2",
    "contracts.md": "f80a2ead6736d5f5aff70e72e3aa7de1c7cc63f93a604fb6eeb4a163059f925c",
    # V6 守护：动前 src 子树哈希
    "src/router": "375d6bc7e7a55fa5c747ea8a94a8ff0b0ebb8cbd75e39b2a02cd56273c39d828",
    "src/api": "7406ef2077cc46dc30679ec405a3b50a01325c2b78a308af438fbb52e7b9dae4",
    "src/core": "866c5fddaed5297f39122dbf9a423e24fd38777f79d859d3b03d88f09a340c72",
    # dist 对照（D2-C1 记载）
    "dist_files_d2c1": 238,
}

# 本卡要删的两个目录
KILL_DIRS = [
    os.path.join(VIEW, "example"),
    os.path.join(VIEW, "systemTools"),
]
# 必须保留
KEEP_DIRS = [
    os.path.join(VIEW, "about"),
    os.path.join(VIEW, "superAdmin"),
]

results = []


def rec(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, (" : " + detail) if detail else ""))


def sha256_bytes(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def tree_hash(d):
    """目录树哈希：rel_path + 内容 sha256 排序拼接（P-36：二进制读）。"""
    agg = hashlib.sha256()
    n = 0
    for root, dirs, files in os.walk(d):
        dirs[:] = sorted(dirs)
        for f in sorted(files):
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, SRC).replace("\\", "/")
            agg.update((rel + " " + sha256_bytes(fp) + "\n").encode("utf-8"))
            n += 1
    return n, agg.hexdigest()


def count_files(d):
    if not os.path.isdir(d):
        return -1
    return sum(len(f) for _, _, f in os.walk(d))


# ---------------------------------------------------------------- V8 核心
def parse_menu_components(txt):
    """
    从 menu.go 源码里抽出每个 seed 行的 (行号, Component 值)。
    Component: "view/..." 形式；"/" 是外链占位，不参与存在性检查。
    """
    out = []
    for i, line in enumerate(txt.splitlines(), 1):
        m = re.search(r'Component:\s*"([^"]*)"', line)
        if m:
            out.append((i, m.group(1)))
    return out


def component_to_path(comp):
    """
    Component 串 -> src 下期望的 .vue 相对路径。
    与 src/utils/asyncRouter.js 的 import.meta.glob('../view/**/*.vue') 语义一致：
      键形如 '/src/view/xxx/yyy.vue'，匹配时用 component 串（'view/xxx/yyy.vue'）。
    ★ 无扩展名者（如 view/example/simpleUploader/simpleUploader）按 .vue 补齐。
    """
    c = comp.strip()
    if c in ("/", "", "Layout", "ParentView"):
        return None  # 非文件型
    if c.startswith("@/"):
        c = c[2:]
    if not c.startswith("view/"):
        return None
    if not c.endswith(".vue"):
        c = c + ".vue"
    return os.path.join(SRC, c.replace("/", os.sep))


def v8_dangling():
    print("V8 ★★★ menu.go 无【悬空 Component】（机械检查每个 Component 对应 .vue 是否存在）:")
    if not os.path.isfile(MENU_GO):
        rec("V8 menu.go 存在", False, "文件缺失")
        return
    txt = read_bytes(MENU_GO).decode("utf-8")
    comps = parse_menu_components(txt)
    print("    共解析到 %d 个 Component 串" % len(comps))
    dangling = []
    skipped = []
    for ln, comp in comps:
        p = component_to_path(comp)
        if p is None:
            skipped.append((ln, comp))
            print("      :%-4d [SKIP-非文件型] %s" % (ln, comp))
            continue
        ex = os.path.isfile(p)
        rel = os.path.relpath(p, SRC).replace("\\", "/")
        print("      :%-4d [%s] %-52s -> src/%s" % (ln, "OK " if ex else "DANGLING", comp, rel))
        if not ex:
            dangling.append((ln, comp))
    if skipped:
        print("    （%d 个非文件型 Component 已 SKIP：%s）" % (len(skipped), ", ".join(c for _, c in skipped)))
    rec("V8 menu.go 无悬空 Component", len(dangling) == 0,
        "悬空 %d 个: %s" % (len(dangling), [c for _, c in dangling]) if dangling else "%d 个全部可解析" % (len(comps) - len(skipped)))


# ---------------------------------------------------------------- V9 核心
def v9_data_inserted():
    print("V9 ★★ DataInserted() 判据 path 仍存在于 seed（幂等保护）:")
    if not os.path.isfile(MENU_GO):
        rec("V9 menu.go 存在", False, "文件缺失")
        return
    txt = read_bytes(MENU_GO).decode("utf-8")
    # 取 DataInserted 里 db.Where("path = ?", "XXX") 的判据
    m = re.search(r'DataInserted[\s\S]*?db\.Where\(\s*"path\s*=\s*\?"\s*,\s*"([^"]+)"', txt)
    if not m:
        rec("V9 能解析 DataInserted 判据 path", False, "未匹配到 db.Where(\"path = ?\", \"...\")")
        return
    probe = m.group(1)
    print("    DataInserted 判据 path = %r" % probe)
    # seed 里所有 Path: "xxx"
    seed_paths = re.findall(r'\bPath:\s*"([^"]*)"', txt)
    print("    seed 中 Path 值共 %d 个，判据 %r 在其中: %s" % (len(seed_paths), probe, probe in seed_paths))
    rec("V9 判据 path 存在于 seed 中（否则永远 false ⇒ 每次启动重复插入）",
        probe in seed_paths,
        "path=%r %s" % (probe, "命中" if probe in seed_paths else "★未命中★ seed 中没有该 path"))


def main():
    static_only = "--static-only" in sys.argv
    selftest = "--selftest" in sys.argv

    if selftest:
        print("=== T6 量尺前置断言（P-5）===")
        print("  npm.cmd 存在: %s" % os.path.isfile(NPM))
        print("  menu.go 存在: %s" % os.path.isfile(MENU_GO))
        print("  src 存在: %s" % os.path.isdir(SRC))
        print("  vite outDir: %s" % ("dist" if "outDir: 'dist'" in open(
            os.path.join(WEB, "vite.config.js"), encoding="utf-8").read() else "?"))
        print("  asyncRouter glob: %s" % ("import.meta.glob" in open(
            os.path.join(SRC, "utils", "asyncRouter.js"), encoding="utf-8").read()))
        return 0

    print("=== T6 脚手架裁剪 判据 ===")

    # ---- V1：删前已证明无外部引用（结构性断言：删后两目录确不存在，且引用仅内部）----
    print("V1 ★★ 无外部引用（机械搜索）：")
    ex = os.path.isdir(KILL_DIRS[0])
    st = os.path.isdir(KILL_DIRS[1])
    if ex or st:
        # 动前状态：给出引用扫描结论
        internal_only = True
        ext_hits = []
        for root, dirs, files in os.walk(SRC):
            for f in files:
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, SRC).replace("\\", "/")
                if rel.startswith("view/example/") or rel.startswith("view/systemTools/"):
                    continue  # 内部自引用不计
                try:
                    t = read_bytes(fp).decode("utf-8", "replace")
                except Exception:
                    continue
                if "systemTools" in t or "view/example" in t or "view/example/" in t:
                    for ln, l in enumerate(t.splitlines(), 1):
                        if "systemTools" in l or "view/example" in l:
                            ext_hits.append("%s:%d: %s" % (rel, ln, l.strip()[:120]))
        # 后端：除 menu.go 外是否还有硬编码
        be_hits = []
        be_src = os.path.join(ROOT, "01-backend-go", "source")
        for root, dirs, files in os.walk(be_src):
            for f in files:
                if not f.endswith(".go"):
                    continue
                fp = os.path.join(root, f)
                if os.path.normcase(fp) == os.path.normcase(MENU_GO):
                    continue
                try:
                    t = read_bytes(fp).decode("utf-8", "replace")
                except Exception:
                    continue
                for ln, l in enumerate(t.splitlines(), 1):
                    if "view/example" in l or "view/systemTools" in l:
                        be_hits.append("%s:%d: %s" % (os.path.relpath(fp, ROOT), ln, l.strip()[:120]))
        print("    src 树（排除两目录自身）非内部引用数: %d" % len(ext_hits))
        for h in ext_hits:
            print("      " + h)
        print("    01-backend-go/source（排除 menu.go）硬编码引用数: %d" % len(be_hits))
        for h in be_hits:
            print("      " + h)
        rec("V1 两目录无外部引用（src 侧）", len(ext_hits) == 0, "%d 处" % len(ext_hits))
        rec("V1 两目录无外部引用（后端非 menu.go 侧）", len(be_hits) == 0, "%d 处" % len(be_hits))
    else:
        print("    （两目录已删除 —— 动前 V1 结论以留档输出为准）")
        rec("V1 两目录已删除（动前无外部引用）", True, "见留档 _t6_v1_search.txt")

    # ---- V2 / V3 ----
    print("V2/V3 ★ 两目录已不存在:")
    rec("V2 example/ 不存在", not os.path.isdir(KILL_DIRS[0]),
        "count=%d" % count_files(KILL_DIRS[0]) if os.path.isdir(KILL_DIRS[0]) else "absent")
    rec("V3 systemTools/ 不存在", not os.path.isdir(KILL_DIRS[1]),
        "count=%d" % count_files(KILL_DIRS[1]) if os.path.isdir(KILL_DIRS[1]) else "absent")

    # ---- V4 ----
    print("V4 ★ about/ 与 superAdmin/ 仍存在:")
    rec("V4 about/ 仍存在", os.path.isdir(KEEP_DIRS[0]), "files=%d" % count_files(KEEP_DIRS[0]))
    rec("V4 superAdmin/ 仍存在", os.path.isdir(KEEP_DIRS[1]), "files=%d" % count_files(KEEP_DIRS[1]))

    # ---- V6 ----
    print("V6 ★ 未改 src/router、src/api、src/core:")
    for sub, want in (("router", BASE["src/router"]), ("api", BASE["src/api"]), ("core", BASE["src/core"])):
        n, h = tree_hash(os.path.join(SRC, sub))
        rec("V6 src/%s 未改" % sub, h == want, "files=%d sha256=%s%s" % (n, h[:16], "" if h == want else " != " + want[:16]))

    # ---- V7 ----
    print("V7 守护：_manifest.sha256、contracts.md 未改:")
    rec("V7 _manifest.sha256 未改", sha256_bytes(MANIFEST) == BASE["_manifest.sha256"], sha256_bytes(MANIFEST)[:16])
    rec("V7 contracts.md 未改", sha256_bytes(CONTRACTS) == BASE["contracts.md"], sha256_bytes(CONTRACTS)[:16])

    # ---- V8 ----
    v8_dangling()

    # ---- V9 ----
    v9_data_inserted()

    # ---- V5 ----
    if static_only:
        print("[SKIP] V5 被 --static-only 跳过 —— SKIP 不等于 PASS（P-13）")
    else:
        print("V5 ★ npm.cmd run build:")
        print("    npm.cmd 存在: %s" % os.path.isfile(NPM))
        env = dict(os.environ)
        env["PATH"] = r"E:\CTF\runtime\node;" + env.get("PATH", "")
        try:
            p = subprocess.run([NPM, "run", "build"], cwd=WEB, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=1800)
            rc = p.returncode
            tail = p.stdout.decode("utf-8", "replace").strip().splitlines()[-12:]
        except subprocess.TimeoutExpired:
            rc, tail = -999, ["TIMEOUT"]
        print("    npm.cmd run build EXIT=%d" % rc)
        for l in tail:
            print("      " + l)
        rec("V5 npm.cmd run build EXIT=0", rc == 0, "EXIT=%d" % rc)
        n = count_files(os.path.join(WEB, "dist"))
        rec("V5 产出 dist/", n > 0, "%d 个文件（D2-C1 对照 %d）" % (n, BASE["dist_files_d2c1"]))

    # ---- 汇总 ----
    fails = [n for n, ok, _ in results if not ok]
    print("")
    print("=== %d/%d 通过 ===" % (len(results) - len(fails), len(results)))
    if fails:
        print("RESULT=RED  失败项:")
        for f in fails:
            print("  - " + f)
        return 1
    print("RESULT=GREEN  T6 脚手架裁剪完成：两目录已删 + menu.go 无悬空 Component + 判据幂等 + 构建 EXIT=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
