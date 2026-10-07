# -*- coding: utf-8 -*-
"""
T29 播种器（WBE01-D · (乙-1)）：把**判据必需的夹具**从业务库 `qk_e2e` 种进测试库。

★ 只种下列 7 张**业务夹具表**（对应 WBE01-D 方案 §4-4）：
    machine · agent · packet · wallet · custom · settlement · token
  ⛔ **不种 `bill`**（判据自己会种；种了会破坏"消失的行"类断言）。
★ 前置：测试库的表必须**已存在** —— 由**实例 B 启动时的 `RegisterTables()` AutoMigrate** 建出
  （同一份 model ⇒ schema 与业务库**同源**）。本播种器**不建表**，只搬行。
★ 列对齐：按 `information_schema` 取**两库列名的交集**（有序），避免"业务库有历史列、新库没有"导致 `SELECT *` 错位。
★ 幂等：先 `DELETE FROM` 目标表再插（只动测试库，⛔ 从不写业务库）。

用法：
    python seed_test_db.py                      # 种进 qk_e2e_test（默认）
    DSH_DB=qk_e2e_test python seed_test_db.py   # 同上（显式）
"""
from __future__ import annotations

import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os as _os
import sys as _sys

_os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os
import subprocess

MD_BIN = IOS_ROOT + r"\_integration\_fix_work\_toolchain\mariadb-11.4.4-winx64\bin"
MYSQL = os.path.join(MD_BIN, "mysql.exe")
DB_PORT = "13306"
SRC_DB = os.environ.get("DSH_SEED_FROM", "qk_e2e")          # 业务库（来源，只读）
DST_DB = os.environ.get("DSH_DB", "qk_e2e_test")            # 测试库（目标）

# ★ 只种这几张夹具表（⛔ 无 bill）
FIXTURE_TABLES = ["machine", "agent", "packet", "wallet", "custom", "settlement", "token"]

# ⛔ 安全闸：目标库不得是业务库
if DST_DB == SRC_DB:
    print(f"⛔ 拒绝：DSH_DB({DST_DB}) == 来源库({SRC_DB}) —— 播种器不得写业务库")
    _sys.exit(2)


def sql(stmt, db=None):
    d = f"USE {db}; " if db else ""
    cmd = [MYSQL, "--skip-ssl", "-h", "127.0.0.1", "-P", DB_PORT, "-u", "root",
           "--default-character-set=utf8mb4", "-B", "-e", f"{d}{stmt}"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def rows(stmt, db=None):
    rc, out = sql(stmt, db)
    if rc != 0:
        return []
    ls = [l for l in out.strip().splitlines() if l.strip()]
    return [l.split("\t") for l in ls[1:]] if ls else []


def cols_of(db, tbl):
    return [r[0] for r in rows(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        f"WHERE TABLE_SCHEMA='{db}' AND TABLE_NAME='{tbl}' ORDER BY ORDINAL_POSITION;")]


def all_tables(db):
    return [r[0] for r in rows(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        f"WHERE TABLE_SCHEMA='{db}' AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME;")]


def clone_schema():
    """★★ T29 关键修正：测试库的结构必须**克隆业务库**，⛔ 不能靠 `AutoMigrate`。

    实测（⌛2026-10-03，本线自造并实测）：
      业务库 `qk_e2e`（**迁移**建的）：`num/usdt_num/total_num` = `varchar(32)`、`transfer_hash/order_id` = `varchar(128)`
      隔离库（**AutoMigrate** 建的，`DefaultStringSize:191`）：上述列全是 **`varchar(191)`**
      ⇒ 列**数**相同、列**类型**不同。后果：`money_path` 的「amount 超精度」用例
         （33 位小数）在业务库因 **"Data too long" 被拒**，在隔离库却**装得下 ⇒ 被接受**
      ⇒ **隔离环境不保真 ⇒ 判据结论"与真实环境无关"**（＝ WBE01-D §6 预警的「播种漂移」）。
    ⇒ 本函数按业务库逐表 `DROP + CREATE TABLE ... LIKE`（**只克隆结构，不搬数据**）。
    """
    src = all_tables(SRC_DB)
    skip = [t for t in src if t.startswith("_bak_")]        # 备份表不克隆
    err = []
    for t in src:
        if t in skip:
            continue
        sql(f"DROP TABLE IF EXISTS `{t}`;", DST_DB)
        rc, out = sql(f"CREATE TABLE `{t}` LIKE {SRC_DB}.`{t}`;", DST_DB)
        if rc != 0:
            err.append(f"{t}: {out.strip()[:100]}")
    print(f"  [schema] 克隆 {len(src) - len(skip)} 张表结构（跳过备份表 {skip}）"
          + (f"  ★ 失败：{err}" if err else ""))
    return not err


def schema_fidelity():
    """核对两库**列类型**是否逐列一致；返回 (缺失表, 类型不符列)。"""
    src, dst = set(all_tables(SRC_DB)), set(all_tables(DST_DB))
    miss = sorted(t for t in src if t not in dst and not t.startswith("_bak_"))
    diff = []
    for t in sorted(src & dst):
        a = {r[0]: r[1] for r in rows(
            "SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS "
            f"WHERE TABLE_SCHEMA='{SRC_DB}' AND TABLE_NAME='{t}';")}
        b = {r[0]: r[1] for r in rows(
            "SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS "
            f"WHERE TABLE_SCHEMA='{DST_DB}' AND TABLE_NAME='{t}';")}
        for c in sorted(set(a) | set(b)):
            if a.get(c) != b.get(c):
                diff.append(f"{t}.{c}: {a.get(c)} → {b.get(c)}")
    return miss, diff


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema-only", action="store_true", help="只克隆结构，不种行")
    a = ap.parse_args()

    print(f"=== T29 播种器 ===\n源库(只读)={SRC_DB}  目标库={DST_DB}  端口={DB_PORT}")
    ok = clone_schema()
    miss, diff = schema_fidelity()
    if miss:
        ok = False
        print(f"  [保真] ★ 缺表 {miss}")
    if diff:
        ok = False
        print(f"  [保真] ★★ 列类型不符 {len(diff)} 处：")
        for d in diff[:12]:
            print(f"          {d}")
    else:
        print("  [保真] ✓ 两库列类型逐列一致")

    if a.schema_only:
        print("SCHEMA=" + ("OK" if ok else "BAD"))
        return 0 if ok else 1

    for t in FIXTURE_TABLES:
        c_src, c_dst = cols_of(SRC_DB, t), cols_of(DST_DB, t)
        if not c_dst:
            print(f"  [FAIL] {t}: 目标库无此表 ⇒ 先启动实例 B 让它 AutoMigrate")
            ok = False
            continue
        common = [c for c in c_src if c in c_dst]
        if not common:
            print(f"  [FAIL] {t}: 两库无公共列")
            ok = False
            continue
        cl = ",".join(f"`{c}`" for c in common)
        sql(f"DELETE FROM `{t}`;", DST_DB)
        rc, out = sql(f"INSERT INTO `{t}` ({cl}) SELECT {cl} FROM {SRC_DB}.`{t}`;", DST_DB)
        n = rows("SELECT COUNT(*) FROM `%s`;" % t, DST_DB)
        n = n[0][0] if n else "?"
        miss = [c for c in c_src if c not in c_dst]
        flag = "OK" if rc == 0 else "FAIL"
        if rc != 0:
            ok = False
        print(f"  [{flag}] {t}: 种 {n} 行（列 {len(common)}/{len(c_src)}"
              + (f"，目标库缺列 {miss}" if miss else "") + (f"）  {out.strip()[:120]}" if rc else "）"))
    # 反向确认：bill 必须是空的（本播种器不种）
    nb = rows("SELECT COUNT(*) FROM `bill`;", DST_DB)
    nb = nb[0][0] if nb else "?"
    print(f"  [检查] 目标库 bill 行数 = {nb}（应为 0 —— 播种器不种 bill）")
    print("SEED=" + ("OK" if ok else "BAD"))
    return 0 if ok else 1


if __name__ == "__main__":
    _sys.exit(main())
