# -*- coding: utf-8 -*-
"""T56 · **判据装置的「独立互证判据」** —— 以**隔离 MariaDB 引擎**为锚，**不共享**装置的任何实现。

★★ 为什么需要它（结构性缺口）：`verify_migration_hygiene.py` **`import`** 应用器的
   `_USE_STMT_RE` / `neutralize`（**单源**）⇒ **两件同源** ⇒ 它们的自检是**自证**、不是**互证**：
   **应用器正则错 ⇒ 判据跟着错**。本件**换一把不共享实现的尺子**。

★ 本件锚的是什么（V4）：**引擎语义** —— 把形态（含装置<产出>）**真喂给隔离 MariaDB**，
   观测「**它到底做了什么**」：
     · `USE` 面：`SELECT DATABASE()` ⇒ 有没有**落到非目标库**；
     · DD 面：`information_schema.SCHEMATA` 的**<ins>属性快照</ins>**（库名 ＋ 默认字符集 ＋ 默认排序）
       ⇒ 有没有**建库／删库／改库属性**（★ `T58`：不止集合差分）。
   ⛔ 本件**不把装置的口径当作真值**：装置只作为**被查对象**（黑盒转换），
     其判定与引擎不符 ⇒ **差集即 Finding**。

★ 与装置的耦合方式（★ 如实披露）：本件**对装置零静态依赖**（★ `T58` 改述，见下），
   而是以 **subprocess + `importlib.import_module`** 把装置当**黑盒**调用，取其 `neutralize()` 的**产出文本**。
   ⇒ 用到的只有「**它产出了什么**」这一件事，⛔ 不用它的正则/掩码做任何判断。
★★ `T58`（`F-T56-2C`）**更硬的证法**（非形态机检）：`main()` 里加**运行时断言**
   `assert_blackbox_no_static_import()` —— **本进程 `sys.modules` 里<ins>不得</ins>出现装置模块**
   ⇒ 证的是「本进程**确实没** import 装置」（运行时事实），而非「grep 数不到 import 字样」。

★ 安全：`USE` 面**零 DDL 零写**（只 `USE <已存在库>` ＋ `SELECT`）；DD 面用**一次性探针库**，
   **跑前重建、跑后 DROP，并复核零残留**。⛔ 全程不碰业务库。

★★ `T58`（`F-T56-A`，**本件第一判据**）：**默认路径**加 **oracle（引擎）可达性断言** ——
   引擎不可达时所有读数退化为空 ⇒ 差集恒为空 ⇒ **假绿**（★ 本轮**真实发生过**：隔离 MySQL 停摆过一次）。
   ⇒ 不可达 ⇒ 打印 `RESULT=RED` 并**非 0 退出**（⛔ 不得 GREEN）。

★★ `T63`（`F-T58-B1`/`B3`/`B4`，均 P3 残余、**非阻断**）：
   ① 探针库**变体清库点**由 `DD_FORMS` **派生**（`probe_dbs()`，⛔ 不再硬编码 `2/3/4`）⇒ 加新形态时清库点**自动跟随**；
   ② 属性快照**限定前缀**（`qk_t56_dd%` ／ `qk_ad09_%`）⇒ 窗口内并发建/删**无关库**不再计入 ⇒ 免**假红**；
   ③ oracle 可达性**不止开头一次** —— 读数读取失败抛 `OracleUnreachable`、判决前**再验一次** ⇒ **大幅收窄**残余假绿；
★ `T63` **返修**（第 1 名复核后 · ⌛2026-10-05）：
   ★ **`F-T63-1`（P2 阻断，本卡引入）** —— ② 的前缀过滤会让**前缀外**的库被删**看不见** ⇒
     `check_dd` **起止各查一次「前缀外哨兵面」**（**前缀外哨兵库** ＋ 只对**「减少」**报红，⛔ 不退回全库快照）；
   ★ **`F-T63-2`（P3，本卡引入）** —— `--selftest` 捕获 `OracleUnreachable` ⇒ 返回 **3**（⛔ 不落 `1`）。

★★ `T65`（⌛2026-10-05 · harm 面扩 **DML 面**）：新增**行数据面锚** `probe_table_stats()` —— 对**我方一次性探针库内的
   探针表**取 `(行数, 内容哈希)`；`DD_FORMS` 增 `TRUNCATE TABLE` ／ 真多语句 `INSERT`/`UPDATE`/`DELETE` ＋ 负例「注释内 DML」。
   ★★ **边界（<ins>有意</ins>，非盲区）**：DML 锚**只看我方探针库** —— ★ 因为「执行**指向别的库**的 DML」正是本判据**禁止**的
   （★ 只碰自己的一次性探针库）⇒ 故对**别的库**的行数据面**不覆盖**，且**不去碰**。
   ★★ **权限面（`GRANT`／`REVOKE`／`CREATE USER`）本版<ins>不实装</ins>（★ 如实登记）**：本机 `13306` 以
   **`--skip-grant-tables`** 运行 ⇒ 权限语句一律 `ERROR 1290`、`information_schema.USER_PRIVILEGES` **0 行**
   ⇒ ★ **本机对权限面<无引擎语义可观测>** ⇒ 而本判据的立场是**锚引擎语义、⛔ 不靠形态**
   ⇒ ★ **不退化**为 `grep GRANT` 式**形态机检**（★ 形态可被静默绕过 —— 见 `T65` 卡 **§六** 裁定）。

用法：
    python verify_migration_independent.py                 # 全量（USE 面 ＋ DD 面）
    python verify_migration_independent.py --use-only       # 只 USE 面（**零 DDL**）
    python verify_migration_independent.py --device <路径>  # 指向某一份装置（供变异对照）
    python verify_migration_independent.py --selftest       # 量尺前置断言（★ 含内置变异对照）
退出码：0 = 无差集（装置产出在引擎上**安全**）；1 = ★ 有差集（Finding）；2 = 量尺自检坏；3 = ★ oracle 不可达。
"""
from __future__ import annotations

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FW = IOS_ROOT + r"\_integration\_fix_work"
DEFAULT_DEVICE = os.path.join(FW, "verify_ad09_schema_migration_diff.py")
MY = os.path.join(FW, r"_toolchain\mariadb-11.4.4-winx64\bin\mysql.exe")

# ★ 目标库（USE 面用已存在的只读系统库当"他库"；⛔ 不用业务库）
OTHER_DB = "mysql"
TMP_DB = "qk_ad09_t56"           # ★ 装置产出里的 USE 会被指到这里；★ 装置护栏要求形如 `qk_ad09_*`（fail-closed，实测）
PROBE_DB = "qk_t56_dd"           # DD 面的一次性探针库
# ★ T65（harm 面扩 **DML 面**）：探针库里的**探针表** —— 作**行数据面**的锚（`TRUNCATE`／`INSERT`／`UPDATE`／`DELETE`）。
PROBE_TABLE = "t"
# ★ T63 返修（`F-T63-1`）：**前缀外**哨兵库 —— 名字**不在** B3 的两条前缀（`qk_t56_dd%`／`qk_ad09_%`）内，
#   用来在 `check_dd` 起止各验一次「前缀外的世界有没有被删」。
SENTINEL_DB = "qk_t63_sentinel_outside"


def dev_neutralize(device_path, sql_text):
    """把装置当**黑盒**：subprocess + import_module 取它的产出文本。⛔ 不静态 import。

    ★★ 为什么要把 `device_path` **先复制成规范名**：装置的模块名是固定的
      （`verify_ad09_schema_migration_diff`）；若直接把"变异件所在的目录"塞进 `sys.path`，
      而变异件用了别的文件名，`import_module` 会**从 cwd 里 import 到原件** ⇒ **`--device` 形同虚设**
      （★ 我在 V2 反向自证里实测踩到：两种变异给出**完全相同**的结果 ✗）。
      ⇒ 复制到临时目录并**沿用它自己的规范文件名** ⇒ `--device` **真的说了算** ✓"""
    d = tempfile.mkdtemp(prefix="t56_")
    # ★ 以**规范名**复制（保持 `import_module` 能解析，同时确保加载的确是 `device_path` 那一份）
    dst = os.path.join(d, os.path.basename(DEFAULT_DEVICE))
    shutil.copyfile(device_path, dst)
    src = os.path.join(d, "in.sql")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(sql_text)
    code = (
        "import sys,importlib,io;"
        "sys.path.insert(0,%r);"
        "m=importlib.import_module('verify_ad09_schema_migration_diff');"
        "sys.stdout.write(m.neutralize(io.open(%r,encoding='utf-8').read()))"
        % (d, src)
    )
    env = dict(os.environ)
    env["AD09_TMP_DB"] = TMP_DB          # ★ 让产出里的 USE 指到我的探针库
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, cwd=d)
    shutil.rmtree(d, ignore_errors=True)
    return p.returncode, (p.stdout or ""), (p.stderr or "").strip()


def run_sql(sql, database=None):
    cmd = [MY, "--skip-ssl", "-h", "127.0.0.1", "-P", "13306", "-u", "root", "-B", "-N"]
    if database:
        cmd.append(database)
    p = subprocess.run(cmd + ["-e", sql], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


# ---------------------------------------------------------------- ★ T58：oracle 可达性 ＋ 黑盒运行时断言
class OracleUnreachable(RuntimeError):
    """★ T63（`F-T58-B4`）：**读数期** oracle 失联 —— 可达性断言不能只在开头做一次。

    ★ 残余假绿：开头断言通过后、引擎**中途**失联 ⇒ 读数退化为空 ⇒ 差集恒空 ⇒ 仍 `GREEN`（点时刻断言的洞）。
    ⇒ 读数点读失败即抛本异常、判决前**重验** ⇒ 调用方**非 0 退出**（⛔ 不得 GREEN）。"""


def assert_oracle_reachable(quiet=False):
    """★ T58（`F-T56-A`）：**默认路径**的 oracle 可达性断言。

    引擎不可达 ⇒ 下面所有读数退化为'''空''' ⇒ 差集恒为空 ⇒ **假绿**（本轮真实发生过）。
    ⇒ 不可达 ⇒ 返回 False（调用方**非 0 退出**，⛔ 不得 GREEN）。
    ★ T63（`F-T58-B4`）：★ 本断言**不止在开头做一次** —— `main()` 判决前**再验一次**；`quiet=True` 供重验时少打印。"""
    rc, out, err = run_sql("SELECT 1;")
    if rc != 0 or out.strip() != "1":
        if not quiet:
            print("  [oracle] ★ 不可达：rc=%s out=%r err=%r" % (rc, out, (err or "")[:160]))
        return False
    if not quiet:
        print("  [oracle] 可达性 OK（SELECT 1 ⇒ %r）" % out.strip())
    return True


def assert_blackbox_no_static_import():
    """★ T58（`F-T56-2C`）：**运行时**证明"本进程没 import 装置"。

    ⛔ 不用 `grep` 数 import 字样（那是形态机检、证不了它声称的事）；
    ⇒ 直接查 `sys.modules`：本进程若**从无** import 装置模块 ⇒ 黑盒关系成立。"""
    leaked = [k for k in list(sys.modules) if "verify_ad09_schema_migration_diff" in k]
    if leaked:
        raise AssertionError("⛔ 本进程静态 import 了装置（黑盒关系不成立）：%s" % leaked)
    print("  [黑盒] 本进程 sys.modules 无装置模块 ✓（运行时证据，非 grep）")


def schema_snapshot():
    """★ T58（`F-T56-2A`/`F-T56-B`）：**属性面快照** —— {库名: (默认字符集, 默认排序)}。

    ★ 只做**集合差分**会漏两类：① `ALTER … CHARACTER SET`（**只改属性、不改集合**）
    ② `DROP x; CREATE x;`（**净 0**：集合差分 `[]/[]`，而库真被删过又重建）。⇒ 故比**属性快照**。

    ★ T63（`F-T58-B3`）：**限定前缀**（`qk_t56_dd%` ＋ `qk_ad09_%`）⇒ 窗口内并发建/删**<ins>无关库</ins>**
      不再计入 ⇒ 免**假红**。★ **残余（如实）**：与本判据**同前缀**的库 —— 即**本判据自身的第二个并发实例** ——
      <ins>仍会被计入</ins> ⇒ 那一路**依旧靠「复核方之间串行」的纪律**，本卡未消除（见 `T63` 记录件 §残余）。
    ★ T63（`F-T58-B4`）：★ 读失败（`rc!=0`）**不再静默返回空** ⇒ 抛 `OracleUnreachable`
      ⇒ 中途失联**不会**退化成"无可观测 ⇒ 看着安全"。"""
    rc, out, err = run_sql(
        "SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME "
        "FROM information_schema.SCHEMATA "
        "WHERE SCHEMA_NAME LIKE 'qk\\_t56\\_dd%' OR SCHEMA_NAME LIKE 'qk\\_ad09\\_%' ORDER BY 1;")
    if rc != 0:
        raise OracleUnreachable("属性快照读取失败（引擎不可达？）rc=%s err=%r" % (rc, (err or "")[:160]))
    snap = {}
    for line in (out or "").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            snap[parts[0]] = (parts[1], parts[2])
    return snap


def outside_snapshot():
    """★ T63 返修（`F-T63-1`）：**前缀外**库名集合 —— `schema_snapshot()` 的**补集**。

    ★ 为什么需要它：`B3` 的前缀过滤（`qk_t56_dd%`／`qk_ad09_%`）修好了**并发建库的假红**，
      但代价是 —— **前缀外的库被删时判据<看不见>** ⇒ 装置产出在**前缀外**造成真实破坏仍判 `GREEN`
      （复核方已用 `DROP DATABASE IF EXISTS \\`qk_t63_evil_probe\\`` 复现，见记录件 §返修）。
    ⇒ 本函数供 `check_dd` **起止各查一次**，只对**「减少」**报红
      （★ 并发**建**库不触发 ⇒ ⛔ 不把 `B3` 修好的假红带回来）。"""
    rc, out, err = run_sql(
        "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA "
        "WHERE NOT (SCHEMA_NAME LIKE 'qk\\_t56\\_dd%' OR SCHEMA_NAME LIKE 'qk\\_ad09\\_%');")
    if rc != 0:
        raise OracleUnreachable("前缀外快照读取失败（引擎不可达？）rc=%s err=%r" % (rc, (err or "")[:160]))
    return set(x.strip() for x in (out or "").splitlines() if x.strip())


def probe_table_stats():
    """★ T65 · **行数据面锚**：探针表 (`PROBE_DB`.`PROBE_TABLE`) 的 `(行数, 内容哈希)`。

    ★ 为什么需要它：`schema_snapshot()` 只看**库属性** ⇒ 对 `TRUNCATE`／`INSERT`／`UPDATE`／`DELETE`
      **完全不可见**（★ 集合与属性都不变）⇒ 那类 harm 会被判成"安全"。
    ★★ **边界（<ins>有意</ins>，非盲区）**：★ 本锚**只看我方一次性探针库里的那张探针表** ——
      ★ 因为「执行**指向别的库**的 DML」正是本判据**禁止**的动作（只碰自己的一次性探针库）
      ⇒ ★ 故对**别的库**的行数据面**不覆盖**、也**不去碰**。
    ★ 读失败同样抛 `OracleUnreachable`（⛔ 不退化成"无可观测 ⇒ 看着安全"）。
    ★★ 但**要分清两件事**：① **表不存在**（★ **合法读数** —— 例如 `DROP DATABASE` 形态把整库连表一起删了）
       ⇒ 返回 `None`；② **连 `information_schema` 都读不到** ⇒ 那才是**引擎不可达** ⇒ 抛异常。
       （★ 二者混淆过一次：`DROP DATABASE` 后读表报 `1146` 被当成"引擎不可达"，`check_dd` 直接炸。）"""
    rc, out, err = run_sql(
        "SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = '%s' AND TABLE_NAME = '%s';" % (PROBE_DB, PROBE_TABLE))
    if rc != 0:
        raise OracleUnreachable("探针表存在性读取失败（引擎不可达？）rc=%s err=%r" % (rc, (err or "")[:160]))
    if (out or "").strip() != "1":
        return None                                  # ★ 表不存在（合法读数）；`None` 与元组可比 ⇒ 状态变化即 harmful
    rc, out, err = run_sql(
        "SELECT COUNT(*), COALESCE(MD5(GROUP_CONCAT(CONCAT_WS('|', id, v) ORDER BY id SEPARATOR ',')), '-') "
        "FROM `%s`.`%s`;" % (PROBE_DB, PROBE_TABLE))
    if rc != 0:
        raise OracleUnreachable("探针表快照读取失败（引擎不可达？）rc=%s err=%r" % (rc, (err or "")[:160]))
    parts = (out or "").strip().split("\t")
    if len(parts) < 2:
        return None
    return (int(parts[0]), parts[1])


def probe_dbs():
    """★ T63（`F-T58-B1`）：一次性探针库**全集** —— 由 `DD_FORMS` **派生**，⛔ 不再硬编码 `2/3/4`。

    凡模板里出现 `{db}<字母数字后缀>` ⇒ 该后缀进集合 ⇒ ★ **新增形态（如创建 `{db}5`）时，清库点自动跟随**，
    ⛔ 不会再「**静默残留** ＋ 下一轮撞『已存在』⇒ 假阴（判据看着安全）」。
    ★ `{db}_x`（`N4` 的表名）后缀以 `_` 起 ⇒ 不匹配 ⇒ ⛔ 不会被当成库名。"""
    sufs = {""}
    for _name, tpl, _expect in DD_FORMS:
        sufs.update(re.findall(r"\{db\}([0-9A-Za-z]*)", tpl))
    return [PROBE_DB + s for s in sorted(sufs)]


def reset_probe(create=True):
    """★ 三件事一起做（缺一则**假阴性** —— 我在自测时踩过）：
       ① 重建主探针库 `PROBE_DB`（给 DROP 类形态一个可删目标）；
       ② ★ **把各形态会创建的那些变体库一并 DROP**（★ T63：集合由 `probe_dbs()` **派生**）—— 否则
          **原件跑**建出来的库仍在，**产出跑**再 `CREATE` 会撞"已存在"而报错 ⇒ 新增=[] ⇒ **看着"安全"（假阴性）**。"""
    for d in probe_dbs():
        run_sql("DROP DATABASE IF EXISTS `%s`;" % d)
    if create:
        # ★ T58／T63（`F-T58-A`/`B2` **因果更正**）：探针库**<ins>显式钉死</ins>**为 latin1/latin1_swedish_ci
        #   ⇒ 各「改属性」形态（一律改为 utf8mb4）才**必然**产生差异；★ 该保证**<ins>不依赖</ins>服务器默认值**
        #   （本机 `@@character_set_server=latin1` 只是**现状**、**非承重** —— 原注释把因果说反了）。
        #   ⇒ ★ **唯一失效条件 ＝ 删掉下面这行显式固定**（⛔ 不是"换台默认非 latin1 的引擎"）。
        run_sql("CREATE DATABASE `%s` CHARACTER SET latin1 COLLATE latin1_swedish_ci;" % PROBE_DB)
        # ★ T65：建**探针表**并播 **1 行** —— ★ 给 DML 面一个**确定的行基线**
        #   （每次 reset 都回到同一初始态 ⇒ 行数/内容哈希可作稳定锚）。随库一起 DROP ⇒ 零残留。
        run_sql("CREATE TABLE `%s`.`%s` (id INT PRIMARY KEY AUTO_INCREMENT, v INT) ENGINE=InnoDB;"
                % (PROBE_DB, PROBE_TABLE))
        run_sql("INSERT INTO `%s`.`%s` (v) VALUES (1);" % (PROBE_DB, PROBE_TABLE))


def engine_use_effect(sql):
    """USE 面：跑完后**落在哪个库**（'<none>' 表示没切）。"""
    rc, out, _ = run_sql(sql + "\nSELECT DATABASE();", database=TMP_DB if False else None)
    last = out.splitlines()[-1].strip() if out else "<none>"
    return "NULL" if last in ("NULL", "") else last


def engine_dd_effect(sql):
    """DD 面：跑完后的**属性快照**差分。返回 (新增, 减少, 属性变)。★ T58：三路（含属性面）。"""
    before = schema_snapshot()
    run_sql(sql)
    after = schema_snapshot()
    added = {k: v for k, v in after.items() if k not in before}
    removed = {k: v for k, v in before.items() if k not in after}
    changed = {k: (before[k], after[k]) for k in before if k in after and before[k] != after[k]}
    return added, removed, changed


# ---------------------------------------------------------------- 形态
# USE 面：(名, SQL, 期望：'switch'＝引擎会切到非目标库 ⇒ 装置必须中和；'noop'＝不该被改)
USE_FORMS = [
    ("P1 朴素 USE",        "USE mysql;",                              "switch"),
    ("P2 同行中段",        "SET @x:=1; USE mysql;",                    "switch"),
    ("P3 块注释夹令牌",     "USE mysql /* c */;",                       "switch"),
    ("P4 版本注释",        "/*!50000 USE mysql */;",                   "switch"),
    ("P5 反引号库名",       "USE `mysql`;",                            "switch"),
    ("N1 字符串内",        "SELECT 'USE mysql';",                     "noop"),
    ("N2 注释内",          "-- USE mysql;",                           "noop"),
]
# DD 面：(名, SQL 模板（{db} 会被换成探针库名）, 期望)
#   ★ T58：新增 ① 属性面形态（D7 ALTER）② ★★ 5 个**真多语句**形态（M1–M5）——
#     序列级缺陷（`T57` 的 `F-T57-1`「吞 `;`」正是序列级，当时两把尺都漏）**须由引擎永久覆盖**。
DD_FORMS = [
    ("D1 DROP DATABASE",   "DROP DATABASE `{db}`;",                   "harm"),
    ("D2 CREATE DATABASE", "CREATE DATABASE `{db}2`;",                "harm"),
    ("D3 版本注释 DROP",    "/*!50000 DROP DATABASE `{db}` */;",        "harm"),
    ("★D4 DROP SCHEMA",    "DROP SCHEMA `{db}`;",                     "harm"),
    ("★D5 CREATE SCHEMA",  "CREATE SCHEMA `{db}3`;",                  "harm"),
    ("★D6 注释夹令牌",      "CREATE /*c*/ DATABASE `{db}4`;",           "harm"),
    ("★D7 ALTER 改属性",    "ALTER DATABASE `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;", "harm"),
    ("★★M1 真多语句 DROP",  "SET @x:=1;\nDROP DATABASE `{db}`;\nSELECT 1;",            "harm"),
    ("★★M2 真多语句 CREATE SCH", "SET @x:=1;\nCREATE SCHEMA `{db}2`;\nSELECT 1;",       "harm"),
    ("★★M3 真多语句 ALTER",  "SET @x:=1;\nALTER DATABASE `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;\nSELECT 1;", "harm"),
    ("★★M4 语句+后续语句",   "CREATE SCHEMA `{db}3`;\nCREATE TABLE t(a int);",          "harm"),
    ("★★M5 版注+后续语句",   "/*!50000 DROP DATABASE `{db}` */;\nSELECT 1;",            "harm"),
    ("★★M6 净0（DROP+CREATE 改属性）", "DROP DATABASE `{db}`;\nCREATE DATABASE `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;", "harm"),
    ("N3 注释内 DDL",      "/* DROP DATABASE `{db}` */;",             "noop"),
    ("N4 非 DB 的 DROP",    "DROP TABLE IF EXISTS `{db}_x`;",          "noop"),
    # ★★ T65（harm 面扩 **DML 面**）：以下形态对**探针表**做行数据操作 —— ★ `schema_snapshot()` **看不见**，
    #   由 `probe_table_stats()`（行数 ＋ 内容哈希）判出。
    ("★T65 D8 TRUNCATE",    "TRUNCATE TABLE `{db}`.`t`;",                              "harm"),
    ("★★T65 M7 多语句 INSERT", "SET @x:=1;\nINSERT INTO `{db}`.`t` (v) VALUES (7);\nSELECT 1;", "harm"),
    ("★★T65 M8 多语句 UPDATE", "SET @x:=1;\nUPDATE `{db}`.`t` SET v = 8;\nSELECT 1;",          "harm"),
    ("★★T65 M9 多语句 DELETE", "SET @x:=1;\nDELETE FROM `{db}`.`t`;\nSELECT 1;",               "harm"),
    ("★T65 N5 注释内 DML",   "/* TRUNCATE TABLE `{db}`.`t` */;",                       "noop"),
]


def check_use(device, fails):
    print("  [USE 面] 引擎 ground truth vs 装置产出：")
    for name, sql, expect in USE_FORMS:
        truth = engine_use_effect(sql)
        switched = (truth == OTHER_DB)
        rc, out, err = dev_neutralize(device, sql)
        if rc != 0:
            print("    %-18s 装置调用失败 rc=%s %s" % (name, rc, err[:60])); fails.append(name + "-devfail"); continue
        out_effect = engine_use_effect(out)
        safe = (out_effect != OTHER_DB)
        # ★★ 第三把尺（**同名量对照**）：**产出必须<ins>可执行</ins>** ——
        #    只在「**原件不报错、产出报错**」时才算畸形；⛔ 否则会把"N4 在无默认库下本就 1046"这类
        #    **量尺自身的产物**误判成装置缺陷（我实测踩过）。
        _rcr, _or, err_raw = run_sql(sql)
        _rco, _oo, err_out = run_sql(out)
        if err_out and not err_raw:
            fails.append("USE-%s-产出畸形：%s" % (name, err_out[:50]))
        tag = "✓" if (safe or not switched) else "★ 差集"
        print("    %-18s 引擎(原件)=%-6s 装置产出落在=%-6s %s%s"
              % (name, truth, out_effect, tag, ("  ｜ 产出报错:" + err_out[:30]) if err_out else ""))
        if switched and not safe:
            fails.append("USE-%s（装置产出仍切到 %s）" % (name, OTHER_DB))


def check_dd(device, fails):
    print("  [DD 面] 引擎 ground truth vs 装置产出（属性快照差分；一次性探针库 %s，跑后 DROP）:" % PROBE_DB)
    # ★★ T63 返修（`F-T63-1`）：`B3` 的**前缀过滤**会让「**前缀外**的库被删」看不见 ⇒ 假绿（P2 阻断）。
    #    ⇒ 起止各查一次**前缀外哨兵面**：① 种一个**前缀外哨兵库**；② 记前缀外库集合，
    #      收尾**只对「减少」报红**（★ 并发**建**库不触发 ⇒ ⛔ 不把 `B3` 修好的假红带回来）。
    run_sql("CREATE DATABASE IF NOT EXISTS `%s`;" % SENTINEL_DB)
    outside_before = outside_snapshot()
    for name, tpl, expect in DD_FORMS:
        raw = tpl.format(db=PROBE_DB)
        reset_probe(True)
        t_base = probe_table_stats()                    # ★ T65：**行基线**（每次 reset 都回到同一初始态）
        truth_new, truth_gone, truth_chg = engine_dd_effect(raw)
        t_truth = probe_table_stats()
        # ★ T65：**行面**也算 harmful —— ★ 否则 `TRUNCATE`/`INSERT`/`UPDATE`/`DELETE` 会被判成"安全"
        harmful = bool(truth_new or truth_gone or truth_chg or (t_truth != t_base))
        reset_probe(True)
        t_base = probe_table_stats()
        rc, out, err = dev_neutralize(device, raw)
        if rc != 0:
            print("    %-18s 装置调用失败 rc=%s" % (name, rc)); fails.append(name + "-devfail"); reset_probe(False); continue
        out_new, out_gone, out_chg = engine_dd_effect(out)
        t_out = probe_table_stats()
        safe = not (out_new or out_gone or out_chg or (t_out != t_base))
        # ★★ 第三把尺（**同名量对照**）：**产出必须可执行** —— 但只在「**原件不报错、产出报错**」时才算，
        #    ⛔ 否则会把"N4 在无默认库下本就 1046"这类**量尺自身的产物**误判成装置缺陷（我实测踩过）。
        _rcr, _or, err_raw = run_sql(raw)
        _rco, _oo, err_out = run_sql(out)
        if err_out and not err_raw:
            fails.append("DD-%s-产出畸形：%s" % (name, err_out[:50]))
        tag = "✓" if (safe or not harmful) else "★ 差集"
        print("    %-18s 原件:新增=%s 减少=%s 属性变=%s 行面=%s ｜ 产出:新增=%s 减少=%s 属性变=%s 行面=%s %s%s"
              % (name, sorted(truth_new), sorted(truth_gone), sorted(truth_chg),
                 "变" if t_truth != t_base else "—",
                 sorted(out_new), sorted(out_gone), sorted(out_chg),
                 "变" if t_out != t_base else "—", tag,
                 ("  ｜ 产出报错:" + err_out[:30]) if err_out else ""))
        if harmful and not safe:
            fails.append("DD-%s（装置产出仍建/删/改库：新增=%s 减少=%s 属性变=%s 行面=%s）"
                         % (name, sorted(out_new), sorted(out_gone), sorted(out_chg),
                            "变" if t_out != t_base else "—"))
        # ★ T63（`F-T58-B1`）：清库点由 `probe_dbs()` **派生**（⛔ 不再硬编码 `2/3/4`）⇒ 新增形态**自动跟随**
        for d in probe_dbs():
            run_sql("DROP DATABASE IF EXISTS `%s`;" % d)
    # ★★ T63 返修（`F-T63-1`）：前缀外哨兵面**收尾复核** —— 只对「减少」报红
    outside_after = outside_snapshot()
    gone = sorted(outside_before - outside_after)
    sentinel_alive = SENTINEL_DB in outside_after
    if gone or not sentinel_alive:
        print("  ★★ 前缀外哨兵面：窗口内**减少**=%s ｜ 哨兵库在位=%s ⇒ **报红**（F-T63-1 盲区）"
              % (gone, sentinel_alive))
        fails.append("DD-OUTSIDE-PREFIX（前缀外库在窗口内**减少**：%s；哨兵库在位=%s）"
                     "⇒ `B3` 前缀过滤盲区（F-T63-1）" % (gone, sentinel_alive))
    else:
        print("  ✓ 前缀外哨兵面：无减少、哨兵库在位")
    run_sql("DROP DATABASE IF EXISTS `%s`;" % SENTINEL_DB)
    reset_probe(False)


def _builtin_mutation_control():
    """★ T58（`F-T56-C`）：**内置变异对照** —— 把装置换成「恒等输出」（**不中和**）⇒
       判据**必须报差集（红）** ⇒ 单命令可证「**本判据非恒绿**」。"""
    md = tempfile.mkdtemp(prefix="t58_mut_")
    mut = os.path.join(md, os.path.basename(DEFAULT_DEVICE))
    with open(mut, "w", encoding="utf-8") as fh:
        fh.write(
            "import importlib.util as U\n"
            "_s = U.spec_from_file_location('_t58_real', %r)\n"
            "_m = U.module_from_spec(_s); _s.loader.exec_module(_m)\n"
            "globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})\n"
            "def neutralize(t):\n    return t   # ★ 变异：恒等（不中和）\n"
            % os.path.abspath(DEFAULT_DEVICE))
    raw = "DROP DATABASE `%s`;" % PROBE_DB
    reset_probe(True)
    rc, out, err = dev_neutralize(mut, raw)
    if rc != 0:
        red = True  # 变异件调用不通 ⇒ 也算"能红"
    else:
        n, g, c = engine_dd_effect(out)
        red = bool(n or g or c)
    shutil.rmtree(md, ignore_errors=True)
    reset_probe(False)
    print("  内置变异（恒等装置，不中和）⇒ 引擎仍建/删/改库 = %s（期望 True ⇒ 判据会红）" % red)
    return red


def selftest():
    print("=== 量尺前置断言 ===")
    ok = True
    # ⓪ ★ T58：oracle 可达（量尺前提）
    if not assert_oracle_reachable():
        print("  [FAIL] oracle 不可达 ⇒ 量尺自检坏"); return 2
    # ① 引擎读数本身要能分辨：真 USE 会切、注释里的不会
    a = engine_use_effect("USE mysql;")
    b = engine_use_effect("-- USE mysql;")
    print("  引擎分辨力：真 USE ⇒ %s ｜ 注释内 ⇒ %s" % (a, b))
    if a != OTHER_DB or b == OTHER_DB:
        print("  [FAIL] 引擎 ground truth 分辨力不足"); ok = False
    else:
        print("  [PASS] 引擎 ground truth 可用")
    # ② ★ T58：属性面分辨力 —— ALTER 改属性必须被快照看出（集合不变）
    reset_probe(True)
    n0, g0, c0 = engine_dd_effect("ALTER DATABASE `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;" % PROBE_DB)
    print("  引擎属性面分辨力：ALTER 改属性 ⇒ 新增=%s 减少=%s 属性变=%s" % (sorted(n0), sorted(g0), sorted(c0)))
    if not c0:
        print("  [FAIL] 属性面信号不足（ALTER 未被看出）"); ok = False
    else:
        print("  [PASS] 属性面信号可用")
    reset_probe(False)
    # ③ 装置黑盒调用可用
    rc, out, err = dev_neutralize(DEFAULT_DEVICE, "USE mysql;")
    print("  装置黑盒调用：rc=%s 产出含探针库=%s" % (rc, TMP_DB in out))
    if rc != 0:
        print("  [FAIL] 装置黑盒调用不通"); ok = False
    else:
        print("  [PASS] 装置可作黑盒被查")
    # ④ ★ T58：内置变异对照（判据非恒绿）
    ok = _builtin_mutation_control() and ok
    print("SELFTEST=%s" % ("OK" if ok else "BAD"))
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default=DEFAULT_DEVICE)
    ap.add_argument("--use-only", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        # ★ T63 返修（`F-T63-2`）：自检期 oracle 失联 **≠** 发现差集 ⇒ 捕获后返回 **3**
        #   （⛔ 不得落到 `1` —— 那会让门禁把「自检期引擎失联」读成「发现了差集」）。
        try:
            return selftest()
        except OracleUnreachable as exc:
            print("")
            print("RESULT=RED  ★ 自检期 oracle 失联（F-T63-2）：%s" % exc)
            return 3

    print("=== T56 · 独立互证判据（锚＝隔离 MariaDB 引擎语义）===")
    print("  被查装置：%s" % a.device)
    # ★ T58（F-T56-2C）：黑盒关系**运行时**证据（本进程不得 import 装置）
    assert_blackbox_no_static_import()
    # ★★ T58（F-T56-A，**本件第一判据**）：**默认路径**先断言 oracle 可达 —— 不可达 ⇒ 非 0 退出、⛔ 不得 GREEN
    if not assert_oracle_reachable():
        print("")
        print("RESULT=RED  ★ oracle 不可达 ⇒ 读数全部退化、差集恒空 ⇒ **不得判 GREEN**（F-T56-A）")
        return 3
    fails = []
    # ★ 先备好装置产出会 `USE` 到的那只临时库（`qk_ad09_*`，装置护栏允许），**跑完删**
    run_sql("CREATE DATABASE IF NOT EXISTS `%s`;" % TMP_DB)
    try:
        check_use(a.device, fails)
        if not a.use_only:
            check_dd(a.device, fails)
        # ★★ T63（`F-T58-B4`）：判决前**重验** oracle —— 开头断言通过后引擎**中途**失联 ⇒ 读数退化 ⇒ ⛔ 不得 GREEN
        if not assert_oracle_reachable(quiet=True):
            print("")
            print("RESULT=RED  ★ 读数期 oracle 失联（F-T58-B4）⇒ 读数不可信 ⇒ ⛔ 不得 GREEN")
            return 3
    except OracleUnreachable as exc:
        print("")
        print("RESULT=RED  ★ 读数期 oracle 失联（F-T58-B4）：%s" % exc)
        return 3
    finally:
        run_sql("DROP DATABASE IF EXISTS `%s`;" % TMP_DB)
    print("")
    if fails:
        print("RESULT=RED  ★ 差集 %d 项：%s" % (len(fails), fails))
        return 1
    print("RESULT=GREEN  无差集（装置产出在引擎上安全）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
