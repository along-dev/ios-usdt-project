-- ============================================================================
-- T26 · B-11 收口：针对【本库实际状态】隐藏脚手架残留菜单
-- ============================================================================
-- 背景（审核 B 的 B-11）：
--   `07-db/migration/20-hide-scaffold-menus.sql` 的判据是
--     `id IN (2,9,14,22) OR name IN ('about','example','systemTools') OR ...`
--   而 **本库（qk_e2e）的菜单 id 是 57-90**（手工 seed 的业务版），
--   且 **example / systemTools 已被 T6 删除**。
--   ⇒ 实测：上述条件在本库【仅命中 1 条】—— `id=65 about`。
--
-- 本脚本：
--   ① 建备份表（`CREATE TABLE IF NOT EXISTS`，只建一次，不覆盖）
--   ② 隐藏本库中【实际存在】的脚手架残留（about）
--   ③ 验收
--
-- ★ 幂等：备份只建一次；UPDATE 幂等。
-- ★ 回滚：见文件末尾。
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 步骤 0：备份（只建一次，绝不覆盖）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `_bak_sys_base_menus_hidden_t26` AS
  SELECT `id`, `hidden`, NOW() AS `backed_up_at` FROM `sys_base_menus` WHERE 1=0;

INSERT INTO `_bak_sys_base_menus_hidden_t26` (`id`, `hidden`, `backed_up_at`)
  SELECT m.`id`, m.`hidden`, NOW()
    FROM `sys_base_menus` m
   WHERE NOT EXISTS (
       SELECT 1 FROM `_bak_sys_base_menus_hidden_t26` b WHERE b.`id` = m.`id`
   );

SELECT '--- 备份表状态（应等于菜单总数）---' AS section;
SELECT COUNT(*) AS backed_up FROM `_bak_sys_base_menus_hidden_t26`;

-- ---------------------------------------------------------------------------
-- 步骤 1：隐藏【本库实际存在】的脚手架残留
--   ★ 用 component/name 判据（不依赖 id），即便 id 变化也成立
-- ---------------------------------------------------------------------------
UPDATE `sys_base_menus` SET `hidden` = 1
 WHERE `name` IN ('about', 'example', 'systemTools')
    OR `component` LIKE 'view/example/%'
    OR `component` LIKE 'view/systemTools/%'
    OR `path` LIKE 'https://www.gin-vue-admin.com%';

SELECT '--- 步骤 1 影响行数 ---' AS section;
SELECT ROW_COUNT() AS affected;

-- ---------------------------------------------------------------------------
-- 验收 1：仍可见的脚手架项（期望 0 行）
-- ---------------------------------------------------------------------------
SELECT '--- 验收1：仍可见的脚手架项（期望 0）---' AS section;
SELECT id, parent_id, path, name, hidden, component
  FROM `sys_base_menus`
 WHERE (`name` IN ('about', 'example', 'systemTools')
     OR `component` LIKE 'view/example/%'
     OR `component` LIKE 'view/systemTools/%'
     OR `path` LIKE 'https://www.gin-vue-admin.com%')
   AND `hidden` = 0;

-- ---------------------------------------------------------------------------
-- 验收 2：hidden 分布（对比执行前 0:32 / 1:2）
-- ---------------------------------------------------------------------------
SELECT '--- 验收2：hidden 分布 ---' AS section;
SELECT `hidden`, COUNT(*) AS n FROM `sys_base_menus` GROUP BY `hidden`;

-- ---------------------------------------------------------------------------
-- 验收 3：业务菜单未被误伤（应仍为 hidden=0）
-- ---------------------------------------------------------------------------
SELECT '--- 验收3：业务顶层菜单（应仍可见）---' AS section;
SELECT id, path, title, hidden FROM `sys_base_menus`
 WHERE parent_id = '0' AND name NOT IN ('about')
 ORDER BY sort;

-- ============================================================================
-- 回滚（需要时手动执行）：
--   UPDATE `sys_base_menus` m
--     JOIN `_bak_sys_base_menus_hidden_t26` b ON b.`id` = m.`id`
--      SET m.`hidden` = b.`hidden`;
-- ============================================================================
