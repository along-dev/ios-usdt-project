# -*- coding: utf-8 -*-
"""T48 · `AD-09` §4.1(b)：**差集判据件** —— 「`schema` 建库 ＋ 全量 `migration/**` ⇒ 目标列/键齐」

★ 判据：只用 `07-db/schema/qianke.sql` 建库（**基线态**）会**缺 6 项**；
        再**依序**跑**有效 forward 集**（`migration/**` 去掉排除集后，共 8 件：
        `10/20/21/22/31/32/50/51`）后 **6 项必须齐**。
★ 排除集（**响亮登记**，⛔ 非静默跳过）：`40-prod-db-hardening.sql`（部署期）·
        两个 `-rollback.sql`（会让「期望 schema」undefine）· `30-casbin-seed.sql`（派生表列别名
        语法在本机 MariaDB 11.4.4 报 1064；且**已被 `31-casbin-seed-v2.sql` 取代**）。
★★ **`USE`／DD 判定口径（T53 收口 + T55 收口，词法级）**：**先按 SQL 词法剥掉注释与字符串**（`--` / `#` / `/* … */` /
        `'…'` / `"…"`），**★ 但版本注释 `/*!…*/`（与 `/*M!…*/`）的<ins>内容算代码</ins>**（MariaDB
        **真的执行它**）——**再按 `;` 分句**，逐句判「**以 `USE` 起头**」／「**以 `CREATE|DROP DATABASE` 起头**」。
        ⇒ 能力口径：**任何位置**（行首 / 语句中段 / 版本注释内）的 `USE <他库>` **都会被中和或响亮失败**。
        ★★ **两条支路同法：最小替换保壳**（`USE` ⇒ 只换库名 token；DD ⇒ 只换**连续代码段**为 `DO 0`）
        —— ⛔ 任何支路都**不整段替换**（否则会吃掉版本注释的收尾 `*/` ⇒ 畸形 SQL，`F-T53-A`）。

★★ 安全设计（本件的**唯一**操作对象是临时库）：
   · 全程只建/用/删**临时库**（默认 `qk_ad09_check`，名字走**白名单**）；
   · ★★ **`USE` 中和** —— `07-db/migration/**` 里有 4 个件（`50-*` / `51-*`，含其 rollback）
     写死了 **`USE qk_e2e;`**（业务库名）。**裸跑会把 DDL 落到业务库**
     （`50-custom-ownership-rollback.sql` 是 `DROP COLUMN`）⇒ 本件在喂给 mysql 之前
     **把 `USE <任意库>;` 改写为 `USE <临时库>;`**，并**剥掉** `CREATE/DROP DATABASE` 语句。
     ★ **T49 修口径**：判定与哨兵**都改为「按 `;` 分句后逐句判」**（旧口径只锚行首 ⇒
       同行中段的 `USE <他库>;` 会漏，见 `F-T48-A`）；且**只原位替换命中语句** ⇒ 其余字节不变。
   · ⛔ **不读也不写**业务库 `qk_e2e`（V4 的业务库对照由**运行外壳**另行只读取，不在本件内）。

用法：
    python verify_ad09_schema_migration_diff.py                 # 正控：全流程 ⇒ 期望 EXIT=0
    python verify_ad09_schema_migration_diff.py --no-migration  # 负控：不跑 migration ⇒ 期望 EXIT=1
退出码：0 = 6 项目标齐；1 = 有红（含断言失败/执行失败）。
"""
from __future__ import annotations

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
USDT_ROOT = _os.environ.get("USDT_ROOT", _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------- 常量
REPO = USDT_ROOT
SCHEMA_SQL = os.path.join(REPO, "07-db", "schema", "qianke.sql")
MIG_DIR = os.path.join(REPO, "07-db", "migration")
SKIP_MIGRATION = "40-prod-db-hardening.sql"      # 自述「部署期执行、不在装测环境运行」，保留常量供打印
# ★★ 排除集（总调度 ⌛2026-10-05 裁「甲」）—— **响亮登记，⛔ 非静默跳过**
SKIP_EXACT = {
    "40-prod-db-hardening.sql":
        "自述「**部署期执行**」，⛔ 不在装测环境运行",
    "30-casbin-seed.sql":
        "① 派生表列别名 `) AS v(p, d, g, m)` 在本机 **MariaDB 11.4.4 报 1064**；"
        "② **已被 `31-casbin-seed-v2.sql` 取代**（其 `:9` 原文：v2 修正 v1 的列别名语法，MariaDB 不支持）",
}
SKIP_SUFFIX = ("-rollback.sql",)                 # rollback 件：会让「期望 schema」undefine

MD_BIN = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin"
MYSQL = os.path.join(MD_BIN, "mysql.exe")
DB_HOST = "127.0.0.1"
DB_PORT = os.environ.get("AD09_DB_PORT", "13306")
TMP_DB = os.environ.get("AD09_TMP_DB", "qk_ad09_check")

# ---------------------------------------------------------------- ★ fail-closed 护栏
# ★ 模块级、**任何连接之前**；口径同 T45（只放行白名单值，其余一律拒）。
assert DB_PORT == "13306", (
    "⛔ 拒绝裸跑：只允许隔离 MySQL 端口 13306（实际 AD09_DB_PORT=%r）" % DB_PORT)
assert re.fullmatch(r"qk_ad09_[A-Za-z0-9_]{1,40}", TMP_DB), (
    "⛔ 拒绝裸跑：临时库名必须形如 qk_ad09_*（实际 AD09_TMP_DB=%r）" % TMP_DB)
# 兜底：即便白名单被改，也不许指向这两个真库
assert TMP_DB not in ("qk_e2e", "qk_e2e_test", "mysql",
                      "information_schema", "performance_schema", "sys"), (
    "⛔ 拒绝裸跑：临时库名不得是业务库/隔离库/系统库（实际 %r）" % TMP_DB)

# ---------------------------------------------------------------- 6 项目标（AD-09 §1.3）
TARGETS = [
    ("machine", "platform",        "column"),
    ("machine", "ios_version",     "column"),
    ("wallet",  "btc_address",     "column"),
    ("wallet",  "btc_private_key", "column"),
    ("bill",    "uk_txhash_role",  "index"),     # ★ 幂等唯一键（`bill` 唯一键）
    ("packet",  "custom_user_id",  "column"),
]


# ---------------------------------------------------------------- 工具
def _mysql(argv, stdin_bytes=None, database=None):
    cmd = [MYSQL, "--skip-ssl", "-h", DB_HOST, "-P", DB_PORT, "-u", "root",
           "--default-character-set=utf8mb4", "-B"]
    if database:
        cmd.append(database)
    cmd.extend(argv)                      # ★ 修正：先前漏拼 argv ⇒ `_sql1()` 静默不执行
    p = subprocess.run(cmd, input=stdin_bytes, capture_output=True, cwd=MD_BIN)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


def _sql1(stmt, database=None):
    rc, out, err = _mysql(["-e", stmt], database=database)
    if rc != 0:
        raise RuntimeError("mysql 失败 rc=%s stmt=%s err=%s" % (rc, stmt[:80], err.strip()[:200]))
    rows = [l for l in out.strip().splitlines() if l.strip()]
    # 首行是列名，取最后一行
    return rows[-1].strip() if rows else ""


# ---------------------------------------------------------------- ★ USE 中和（T49 修：按 `;` 分句）
# ★ 判定口径（T49）：**按 `;` 分句后逐句判 `USE`**，跳过 行注释／块注释／字符串／反引号标识符。
#   ⛔ 旧口径 `re.match(r"(?i)^use\s+…", line)` **只锚行首** ⇒ 同行中段的 `USE <他库>;` 双漏
#      （`F-T48-A`；当下影响 0，但那是**本装置自己的洞**）。⛔ 未改任何 `migration/**`。
#   ★ 保留一个**测试杠杆**：`_USE_ANCHOR="line"` 复现旧口径 ⇒ 供自检证明「判定改回 `^` ⇒ 必红」。
_USE_ANCHOR = "stmt"        # "stmt"（现行）| "line"（旧口径，仅供自检复现）

# ★★ T51 收口（`F-T49-A`，P2）：判定由「语句**恰好**是 `USE <ident>`」改为
#    「语句**以 `USE` 关键字起头**」——收的是**能力口径**，不是形态口径：
#    `USE qk_e2e /* prod */;` · `USE qk_e2e -- prod\n;` 之流**不能再静默放行**。
_USE_HEAD_RE = re.compile(r"(?is)^\s*use\b")
_USE_STMT_RE = re.compile(r"(?is)^\s*use\b\s*[`\"']?([A-Za-z0-9_]+)")
_DD_STMT_RE = re.compile(r"(?is)^\s*(create|drop|alter)\s+(database|schema)\b")
# ★★ T57（`F-T55-A`/`F-T56-2A`）：DD 面**能力口径** —— `database|schema`（MariaDB 文档同义词）＋
#    补 `alter`（`ALTER DATABASE/SCHEMA … CHARACTER SET` 会**真改库属性**，引擎实测）。
# ★ T57（`F-T55-C`）：**残留**检查用（**锚<整条语句>**，⛔ 不锚起头）—— 哨兵与 `hygiene.A6` 同用这一条。
_DD_ANY_RE = re.compile(r"(?is)(?<![A-Za-z0-9_])(create|drop|alter)\s+(database|schema)\b")
_LEGACY_USE_RE = re.compile(r"(?i)^use\s+[`\"']?[A-Za-z0-9_]+[`\"']?\s*;")


def _code_mask(sql_text):
    """★ T53（`F-T51-A`）：逐字符标注「是否属于**会被执行**的代码」。
       · 行注释（`-- ` / `#`）· 块注释（`/* … */`）· 字符串（`'…'` / `"…"`）⇒ **trivia**
       · ★★ **版本注释**（`/*!…*/` 与 `/*M!…*/`）的**内容算代码** —— MySQL/MariaDB **真的执行它**
         （本机隔离 MySQL 现读实测：`SELECT 1 /*!50003 + 2 */` ⇒ **3**；普通 `/* */` ⇒ 1）
         ⇒ 只把 `/*!` ＋ 版本号 与收尾 `*/` 记为 trivia，内容**原样**参与分句与判定。
       ★ 旧口径（≤`T51`）把 `/*!…*/` 整段当普通块注释跳过 ⇒ 其内 `USE` **静默放行**（`F-T51-A`）。"""
    n = len(sql_text)
    mask = bytearray(b"\x01" * n)
    i = 0
    while i < n:
        c = sql_text[i]
        if c == "-" and sql_text.startswith("--", i) and (i + 2 >= n or sql_text[i + 2] in " \t\r\n"):
            j = sql_text.find("\n", i); j = n if j < 0 else j
            for k in range(i, j): mask[k] = 0
            i = j; continue
        if c == "#":
            j = sql_text.find("\n", i); j = n if j < 0 else j
            for k in range(i, j): mask[k] = 0
            i = j; continue
        if c == "/" and sql_text.startswith("/*", i):
            j = sql_text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            if sql_text.startswith("/*M!", i):                 # MariaDB 版本注释 `/*M!100100 … */`
                p, ver = i + 4, True
            elif sql_text.startswith("/*!", i):                # MySQL 版本注释 `/*!50003 … */`
                p, ver = i + 3, True
            else:
                p, ver = i, False
            if ver:
                q = p
                while q < max(j - 2, p) and sql_text[q].isdigit():
                    q += 1
                for k in range(i, min(q, j)): mask[k] = 0      # `/*!50003` / `/*M!100100`
                for k in range(max(j - 2, i), j): mask[k] = 0  # 收尾 `*/`
            else:
                for k in range(i, j): mask[k] = 0
            i = j; continue
        if c in "'\"":
            q, k = c, i + 1
            while k < n:
                if sql_text[k] == "\\":
                    k += 2; continue
                if sql_text[k] == q:
                    if k + 1 < n and sql_text[k + 1] == q:     # '' / "" 转义
                        k += 2; continue
                    k += 1; break
                k += 1
            for m in range(i, k): mask[m] = 0
            i = k; continue
        i += 1
    return mask


def _statements(sql_text):
    """★ T53：**先词法标注，再<ins>只在代码位</ins>按 `;` 分句**。
       返回 `(spans, mask)`；`spans = [(start, end_含分号)]`。"""
    mask = _code_mask(sql_text)
    n = len(sql_text)
    spans, start = [], 0
    for i in range(n):
        if sql_text[i] == ";" and mask[i]:
            spans.append((start, i + 1)); start = i + 1
    if any(mask[k] for k in range(start, n) if sql_text[k].strip()):
        spans.append((start, n))
    return spans, mask


def _code_view(sql_text, s, e, mask):
    """语句的**代码视图**：剥掉 trivia 后的字符串 ＋ 每个字符在原串中的偏移。"""
    pos = [k for k in range(s, e) if mask[k]]
    return "".join(sql_text[k] for k in pos), pos


def code_level_uses(sql_text):
    """★ **单源**：列出**代码级**（含版本注释内）的 `USE <库>` 名；解析不出者记 `<USE 无法解析>`。"""
    out = []
    spans, mask = _statements(sql_text)
    for (s, e) in spans:
        code, _pos = _code_view(sql_text, s, e, mask)
        if _USE_HEAD_RE.match(code):
            m = _USE_STMT_RE.match(code)
            out.append(m.group(1) if m else "<USE 无法解析>")
    return out


def _line_of(sql_text, offset):
    return sql_text.count("\n", 0, offset) + 1


def _dd_neutralize_runs(sql_text, mask, pos):
    """★ T57（＋ **`F-T57-1` 修订**）：把一条 DD 语句的**全部代码段**中和 ——
       **首个「非空白核心」⇒ `DO 0`**；**其余非空白核心 ⇒ 删**；
       ★★ **段首/段末<ins>空白</ins>原样保留** ＋ **段末的 `;` <ins>一律保留</ins>**
       （⛔ 不吞语句分隔符/换行 ⇒ `F-T57-1`：**多语句产物粘连**）。
       ★ 只动**代码**字符 ⇒ 版本注释外壳 `/*!…*/`、`/*M!…*/` 与前后注释**逐字节保全**（`F-T53-A`）；
       ★ 且**不留任何 DDL 残留**（`F-T55-C`）。
       ★ 依据（改前护栏，从 `_T57_bak_20261005/…:273-276` 取回）：
         `if sql_text[run_end] == ";": edits.append((k, run_end, "DO 0"))` ⇒ **替换区间不含段末 `;`**。"""
    runs, i = [], 0
    while i < len(pos):                                   # 把代码偏移切成**连续段**（闭区间）
        j = i
        while j + 1 < len(pos) and pos[j + 1] == pos[j] + 1:
            j += 1
        runs.append((pos[i], pos[j]))
        i = j + 1
    out, placed = [], False
    for (a, b) in runs:
        ca, cb = a, b                                     # ★ 收窄到「非空白核心」（段首/段末空白 ⇒ 保留）
        while ca <= cb and sql_text[ca].isspace():
            ca += 1
        while cb >= ca and sql_text[cb].isspace():
            cb -= 1
        if ca > cb:
            continue                                      # ★ 纯空白段 ⇒ 原样
        semi = (sql_text[cb] == ";")                      # ★ 段末分号 ⇒ **保留**
        if semi and ca == cb:
            continue                                      # ★ 恰为 `;` 的段 ⇒ 原样
        end = cb if semi else cb + 1                      # ★★ 替换区间**不含**段末 `;`
        if not placed:
            out.append((ca, end, "DO 0")); placed = True   # ★ 首个非空白核心 ⇒ 无害空操作
        else:
            out.append((ca, end, ""))                     # ★ 其余非空白核心 ⇒ 删除（⛔ 不留残留）
    return out


def neutralize(sql_text):
    """★ 把 `USE <任意>;` 改写为 `USE <临时库>;`；剥掉 CREATE/DROP DATABASE 语句。
       （依据：`07-db/migration/50-*.sql:26` / `50-*-rollback.sql:14` / `51-*.sql:56`
        / `51-*-rollback.sql:13` 写死 `USE qk_e2e;` —— 业务库名。）

       ★ T49：判定改为**按 `;` 分句**；且**只原位替换命中语句** ⇒ 其余字节**逐字节不变**。"""
    if _USE_ANCHOR == "line":                       # ★ 测试杠杆：旧口径（行首锚定）
        out = []
        for line in sql_text.splitlines():
            s = line.strip()
            if _LEGACY_USE_RE.match(s):
                out.append("USE `%s`;" % TMP_DB); continue
            if re.match(r"(?i)^(create|drop)\s+database\b", s):
                out.append("-- [AD09 已剥] " + line); continue
            out.append(line)
        text = "\n".join(out)
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("--") or s.startswith("#"):
                continue
            m = re.match(r"(?i)^use\s+[`\"']?([A-Za-z0-9_]+)", s)
            if m and m.group(1) != TMP_DB:
                raise AssertionError("⛔ USE 中和后仍残留他库：%s（第 %d 行）" % (m.group(1), i))
        return text

    spans, mask = _statements(sql_text)
    edits = []
    for (s, e) in spans:
        code, pos = _code_view(sql_text, s, e, mask)   # ★ T53：代码视图（剥 trivia；版本注释**剥壳**）
        if not pos:
            continue                                   # 整条都是 trivia（纯注释/纯字符串）⇒ ⛔ 不动
        if _USE_HEAD_RE.match(code):                   # ★ 以 `USE` **起头**即入网（能力口径）
            m_use = _USE_STMT_RE.match(code)
            if not m_use:                              # ★ fail-closed：解析不出库名 ⇒ **响亮失败**
                raise AssertionError(
                    "⛔ 语句以 USE 起头但解析不出库名（第 %d 行）：%r"
                    % (_line_of(sql_text, pos[0]), " ".join(code.split())[:80]))
            a, b = m_use.start(1), m_use.end(1)        # ★ 只换**库名 token**（最小替换 ⇒ 其余字节不动）
            if a - 1 >= 0 and code[a - 1] in "`\"'":   #    带引号者**连引号一起换** ⇒
                a -= 1                                 #    ⛔ 避免生成 `` ``tmp`` `` 这种双重引号
            if b < len(code) and code[b] in "`\"'":
                b += 1
            edits.append((pos[a], pos[b - 1] + 1, "`%s`" % TMP_DB))
        elif _DD_STMT_RE.match(code):
            # ★★ T55（`F-T53-A`）＋ **T57 收口**：与 `USE` 支路**同法** —— **最小替换保壳**
            #   （⛔ 不整段替换，否则会吃掉版本注释的收尾 `*/` ⇒ 畸形 SQL）。
            #   ★ T57：把该语句的**<ins>全部</ins>代码段**一并处理（见 `_dd_neutralize_runs`）——
            #     ⛔ 旧法只动「自关键字起的**首段**」⇒ `DROP /*c*/ DATABASE x;` 会**留下 `DATABASE x` 残留**
            #        （`F-T55-C`：判据看不出、引擎侧是语法错）。
            edits.extend(_dd_neutralize_runs(sql_text, mask, pos))
    text = sql_text
    for (a, b, rep) in reversed(edits):                # 逆序替换 ⇒ 偏移不失效
        text = text[:a] + rep + text[b:]
    # ★★ 哨兵：中和之后**任何一条代码级语句**都不许再指向他库（★ 版本注释内同样抓得到）
    spans2, mask2 = _statements(text)
    for (s, e) in spans2:
        code, pos = _code_view(text, s, e, mask2)
        if not pos:
            continue
        if _USE_HEAD_RE.match(code):
            m = _USE_STMT_RE.match(code)
            if (not m) or m.group(1) != TMP_DB:
                raise AssertionError("⛔ USE 中和后仍残留他库/无法解析：%s（第 %d 行）"
                                     % ((m.group(1) if m else "<无法解析>"), _line_of(text, pos[0])))
        # ★★ T57（`F-T55-C`）：DD 残留检查**锚<整条语句>**（⛔ 不锚起头）—— `DO 0/*c*/ DATABASE x;`
        #    这种"起头已不是 DDL、中段却有残留"的形态，起头锚定会漏 ⇒ 这里用 `search`。
        if _DD_ANY_RE.search(code):
            raise AssertionError("⛔ DD 中和后仍残留 `create|drop|alter (database|schema)`"
                                 "（第 %d 行）：%r" % (_line_of(text, pos[0]), " ".join(code.split())[:70]))
    return text


def apply_sql_file(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8", "replace")
    rc, out, err = _mysql([], database=TMP_DB, stdin_bytes=neutralize(text).encode("utf-8"))
    if rc != 0:
        raise RuntimeError("应用 SQL 失败 rc=%s file=%s err=%s"
                           % (rc, os.path.basename(path), err.strip()[-500:]))
    return out


def probe(table, name, kind, db):
    if kind == "column":
        return int(_sql1(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='%s' AND COLUMN_NAME='%s';" % (db, table, name)))
    return int(_sql1(
        "SELECT COUNT(*) FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='%s' AND INDEX_NAME='%s';" % (db, table, name)))


def uk_is_real(db):
    """★「唯一键真存在」—— 不只看名字：须 NON_UNIQUE=0 且列序 = (transfer_hash, role)。"""
    rc, out, _ = _mysql(["-e",
        "SELECT NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA='%s' AND TABLE_NAME='bill' AND INDEX_NAME='uk_txhash_role' "
        "ORDER BY SEQ_IN_INDEX;" % db])
    rows = [l.split("\t") for l in out.strip().splitlines()[1:] if l.strip()]
    if not rows:
        return False, "索引不存在"
    if any(r[0] != "0" for r in rows):
        return False, "NON_UNIQUE=%s（不是唯一键）" % rows[0][0]
    cols = [r[2] for r in rows]
    if cols != ["transfer_hash", "role"]:
        return False, "列序=%s（应 ['transfer_hash','role']）" % cols
    return True, "NON_UNIQUE=0 · 列序=['transfer_hash','role']"


def all_migrations():
    return sorted(f for f in os.listdir(MIG_DIR) if f.lower().endswith(".sql"))


def excluded_map():
    """★ 返回 {被排除件: 理由} —— 打印用，保证**排除是响亮的**。"""
    ex = {}
    for n in all_migrations():
        if n in SKIP_EXACT:
            ex[n] = SKIP_EXACT[n]
        elif n.lower().endswith(SKIP_SUFFIX):
            ex[n] = "rollback 件 —— 会让「期望 schema」undefine，且其无害**只依赖字典序侥幸**"
    return ex


def migration_order():
    """★ **只跑有效 forward 迁移**（总调度 ⌛2026-10-05 两度改判）：
       排除 `40-prod-db-hardening.sql`（部署期）· 两个 `-rollback.sql` · `30-casbin-seed.sql`（语法不可执行且已被 31 取代）。
       ⇒ 应用集 = `10/20/21/22/31/32/50/51`（8 件）。"""
    ex = excluded_map()
    return [n for n in all_migrations() if n not in ex]


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-migration", action="store_true",
                    help="★ 负控：第④步不跑 migration（基线态直接进第⑤步 ⇒ 必红）")
    a = ap.parse_args()

    print("=== T48 · AD-09 差集判据（临时库 %s @ %s:%s）===" % (TMP_DB, DB_HOST, DB_PORT))
    # ★★ T51（`F-T48-B`）：排除集提到 `try` **之外**打印 ⇒ **任何失败路径**（含 ③ 抛错/连不上库）
    #    日志里都能看见「排除了什么、为什么」
    _ex, _order = excluded_map(), migration_order()
    print("  [排除集] ★ 响亮登记（⛔ 非静默跳过）—— 在任何失败路径上都可见：")
    for _n in sorted(_ex):
        print("        ✗ %s ｜ %s" % (_n, _ex[_n]))
    ok = True
    try:
        rc, _, _ = _mysql(["-e", "SELECT 1;"])
        if rc != 0:
            print("★ 连不上隔离 MySQL ⇒ 终止"); return 2

        # ① 建临时库
        _sql1("DROP DATABASE IF EXISTS `%s`;" % TMP_DB)
        _sql1("CREATE DATABASE `%s` DEFAULT CHARACTER SET utf8mb4;" % TMP_DB)
        print("  [1] 临时库已建：%s" % TMP_DB)

        # ② schema 建库（基线态）
        apply_sql_file(SCHEMA_SQL)
        print("  [2] 基线态已建（schema/qianke.sql）")

        # ③ 断言基线【缺】6 项
        base_missing = []
        for t, n, k in TARGETS:
            if probe(t, n, k, TMP_DB) == 0:
                base_missing.append("%s.%s(%s)" % (t, n, k))
        print("  [3] 基线缺项 %d/%d：%s" % (len(base_missing), len(TARGETS), ", ".join(base_missing) or "—"))
        base_ok = (len(base_missing) == len(TARGETS))

        # ④ 依序跑「有效 forward 集」（★ 排除集已在 try 之外打印过，此处只打应用集）
        order = _order
        if a.no_migration:
            print("  [4] ★ --no-migration：**不跑任何迁移**（负控）")
        else:
            print("  [4] 依序应用有效 forward 集（%d 件）：" % len(order))
            for n in order:
                print("        - %s" % n)
                apply_sql_file(os.path.join(MIG_DIR, n))

        # ⑤ 断言补齐态【有】6 项
        present, missing = [], []
        for t, n, k in TARGETS:
            if probe(t, n, k, TMP_DB) > 0:
                present.append("%s.%s" % (t, n))
            else:
                missing.append("%s.%s(%s)" % (t, n, k))
        uk_ok, uk_note = uk_is_real(TMP_DB)
        print("  [5] 补齐态命中 %d/%d：%s" % (len(present), len(TARGETS), ", ".join(present) or "—"))
        print("      ★ uk_txhash_role 真存在？%s（%s）" % ("是" if uk_ok else "否", uk_note))

        # 判读：★ 硬断言：③「基线必缺全部目标项」＋ ⑤「补齐后全在且 uk 为真唯一键」
        #      ⛔ 不给负控开后门（否则就是恒绿）；★ T51（`F-T48-C`）：**分三类打印**，
        #      不让读者只看到笼统的「★ 红」再回头自己找是 [3] 还是 [5]
        ok = (base_ok and len(missing) == 0 and uk_ok)
        tag = "负控(--no-migration)" if a.no_migration else "正控"
        print("  [判读] %s：命中 %d/%d" % (tag, len(present), len(TARGETS)))
        _cls = []
        if not base_ok:
            _cls.append("(i) **基线前提破** —— schema 建库后目标项**已存在 %d/%d**（期望**全缺**）；"
                        "若 `schema/qianke.sql` 被补齐（`07-db/README.md` §④ 明令禁止的回写）⇒ 本判据前提失效"
                        % (len(TARGETS) - len(base_missing), len(TARGETS)))
        if missing:
            _cls.append("(ii) **迁移未生效** —— 补齐态仍缺 %d 项：%s" % (len(missing), ", ".join(missing)))
        if not uk_ok:
            # ★ T53（`F-T51-B`）：三类**可共现**（信息更全），但 (iii) 在 **(ii) 成立时措辞须避免误导**
            #   —— 否则读者会以为"该唯一键不是真唯一键"，而真成因是"迁移根本没跑"。
            if missing:
                _cls.append("(iii) **uk 非真唯一键** —— %s ｜ ★ **但补齐态本就缺 %d 项（见 (ii)）** "
                            "⇒ 该现象多半是 **(ii) 的后果**，⛔ 不是独立的第三个缺陷"
                            % (uk_note, len(missing)))
            else:
                _cls.append("(iii) **uk 非真唯一键** —— %s" % uk_note)
        if _cls:
            for _c in _cls:
                print("        ✗ %s" % _c)
            print("        ⇒ ★ 红（退出码 1）")
        else:
            print("        ⇒ OK")
    except Exception as e:                                            # noqa: BLE001
        ok = False
        print("  ★ 异常：%s" % e)
    finally:
        # ⑥ 清理临时库（成败都清）
        try:
            _sql1("DROP DATABASE IF EXISTS `%s`;" % TMP_DB)
            left = _sql1("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='%s';" % TMP_DB)
            print("  [6] 临时库已清：残留计数=%s" % left)
        except Exception as e:                                        # noqa: BLE001
            print("  ★ 清理失败（须人工处置）：%s" % e)
            ok = False

    print("AD09_DIFF=" + ("OK" if ok else "BAD"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
