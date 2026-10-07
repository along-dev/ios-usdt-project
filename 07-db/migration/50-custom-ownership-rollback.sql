-- ============================================================================
-- WBE01-A 卡A · 阶段2 建列迁移 **回滚件**（一条命令）
-- 件名：50-custom-ownership-rollback.sql
-- 配套：50-custom-ownership.sql
-- ----------------------------------------------------------------------------
-- 用法：mysql --skip-ssl -u root -h 127.0.0.1 -P 13306 < 本件
-- 效果：撤掉 packet.custom_user_id，回到建模前。
--
-- ★ 完整性边界（如实声明）：本列**若已被回填过**（运营绑定了客户），DROP COLUMN 会**丢掉绑定关系**。
--   ⇒ 回滚前**必须先导出**当前绑定：
--        SELECT id, custom_user_id FROM packet;      → 落 _fix_work/_wbe01a_bindings_<时间>.tsv
--   这是**人工步骤**，不在本件的自动范围内 —— 明写，不假装已自动化。
-- ============================================================================
-- ★ T52（`T49-C`）：**原此处写死目标库的 `USE` 语句，已于本轮删除** —— 目标库**只由应用器决定**。
--   ★ 它曾**击穿**应用器的 `<db>` 实参（`mysql … <db> < 本件.sql` 里传别的库也会被它切走）⇒ 删后
--     传错库/不传库会**当场报 `1046 No database selected`**，⛔ 不再静默把 DDL 打到业务库。

ALTER TABLE `packet` DROP COLUMN IF EXISTS `custom_user_id`;

-- ---------- 生效自证（期望 col_exists = 0）----------
SELECT 'SELF-CHECK-DOWN' AS section, COUNT(*) AS col_exists
  FROM information_schema.columns
 WHERE table_schema = DATABASE() AND table_name = 'packet' AND column_name = 'custom_user_id';
