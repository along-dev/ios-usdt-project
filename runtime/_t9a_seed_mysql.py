# -*- coding: utf-8 -*-
"""T9-a：造 MariaDB qk_e2e.machine 的 android 维度种子。

★ 现状：machine 仅 1 行（dev-e2e-001 / ios / 18.5 / status=1）
★ 目标：补 android 维度（≥2 版本）+ ios 的第 2 版本，使看板有意义。

★ 幂等：先删 device_id LIKE 't9seed-%' 再插入。
★ 连接：127.0.0.1:13306，root，空密码，库 qk_e2e。
"""
import io
import sys

try:
    import pymysql
except ImportError:
    print("  ★ pymysql 未安装 ⇒ 尝试用 mysql.connector")
    pymysql = None

if pymysql is None:
    try:
        import mysql.connector as _mc
    except ImportError:
        print("  ★ 两个 MySQL 驱动都没有 ⇒ 改用 CLI")
        sys.exit(2)

CONF = dict(host="127.0.0.1", port=13306, user="root", password="", database="qk_e2e",
            charset="utf8mb4")

ROWS = [
    # (device_id, platform, android_version, ios_version, status, brand, model)
    ("t9seed-android-14-1", "android", "14", "", 1, "Samsung", "SM-G991"),
    ("t9seed-android-14-2", "android", "14", "", 1, "Xiaomi", "M2101K9C"),
    ("t9seed-android-14-3", "android", "14", "", 0, "OPPO", "CPH2207"),
    ("t9seed-android-13-1", "android", "13", "", 1, "Huawei", "ELE-L29"),
    ("t9seed-android-13-2", "android", "13", "", 0, "vivo", "V2045"),
    ("t9seed-ios-18.5-1", "ios", "", "18.5", 1, "Apple", "iPhone14,5"),
    ("t9seed-ios-17.2.1-1", "ios", "", "17.2.1", 1, "Apple", "iPhone12,1"),
    ("t9seed-ios-17.2.1-2", "ios", "", "17.2.1", 0, "Apple", "iPhone13,2"),
]

conn = pymysql.connect(**CONF)
cur = conn.cursor()

cur.execute("DELETE FROM machine WHERE device_id LIKE 't9seed-%%'")
print("  [machine] 清理旧种子: %d" % cur.rowcount)

sql = ("INSERT INTO machine (device_id, platform, android_version, ios_version, "
       "status, brand, model, country, create_time) "
       "VALUES (%s, %s, %s, %s, %s, %s, %s, 'CN', NOW())")
for r in ROWS:
    cur.execute(sql, (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
conn.commit()
print("  [machine] 插入 %d 条" % len(ROWS))

cur.execute("SELECT COUNT(*) FROM machine")
print("  [machine] 现有总数: %d" % cur.fetchone()[0])

print("")
print("  === 造完后的聚合（platform × version）===")
cur.execute("""
    SELECT platform,
           COALESCE(NULLIF(ios_version,''), NULLIF(android_version,''), '(空)') AS ver,
           COUNT(*) AS total,
           SUM(status = 1) AS success
      FROM machine
     GROUP BY platform, ver
     ORDER BY platform, ver
""")
print("    %-10s %-12s %-8s %-8s" % ("platform", "version", "total", "success"))
for row in cur.fetchall():
    print("    %-10s %-12s %-8s %-8s" % (row[0], row[1], row[2], row[3]))

cur.close()
conn.close()
print("")
print("  SEED_MYSQL=OK")
