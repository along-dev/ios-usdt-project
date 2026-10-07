-- ============================================================================
-- WBE01-A 卡A · 阶段1 补记迁移 **回滚件**（一条命令）
-- 件名：51-customusdtnum-agentusdtnum-backfill-rollback.sql
-- 配套：51-customusdtnum-agentusdtnum-backfill.sql
-- 快照：E:\ios漏洞\_integration\_fix_work\_wbe01a_backfill_snapshot_20261003T091611+0800.tsv
--   实测内容（补记前）：custom(1,201,'0') · agent(1,101,'0') · agent(5,9,'0')
-- ----------------------------------------------------------------------------
-- 用法：mysql --skip-ssl -u root -h 127.0.0.1 -P 13306 < 本件
-- 效果：把两张表恢复到补记前的原值。
-- 说明：原值**逐行都是 '0'**（快照实读），故直接写回常量；
--       同时保留"按快照件恢复"的等价做法（见件末注释）作为第二道保险。
-- ============================================================================
-- ★ T52（`T49-C`）：**原此处写死目标库的 `USE` 语句，已于本轮删除** —— 目标库**只由应用器决定**。
--   ★ 它曾**击穿**应用器的 `<db>` 实参（`mysql … <db> < 本件.sql` 里传别的库也会被它切走）⇒ 删后
--     传错库/不传库会**当场报 `1046 No database selected`**，⛔ 不再静默把 DDL 打到业务库。

START TRANSACTION;

UPDATE `custom` SET `usdt_num` = '0' WHERE `id` = 1 AND `user_id` = 201;
UPDATE `agent`  SET `usdt_num` = '0' WHERE `id` = 1 AND `user_id` = 101;
UPDATE `agent`  SET `usdt_num` = '0' WHERE `id` = 5 AND `user_id` = 9;

SELECT 'ROLLED-BACK' AS section, 'custom' AS tbl, id, user_id, usdt_num FROM `custom`;
SELECT 'ROLLED-BACK' AS section, 'agent'  AS tbl, id, user_id, usdt_num FROM `agent`;

COMMIT;

-- 期望回显：三行 usdt_num 均回到 '0'
--
-- ★ 第二道保险（若快照件在，可改用按快照逐行恢复；本表仅 3 行，上面已写死）：
--   快照格式（TSV）：tbl \t id \t user_id \t usdt_num
--   custom	1	201	0
--   agent	1	101	0
--   agent	5	9	0
