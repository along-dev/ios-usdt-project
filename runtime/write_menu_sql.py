import os as _os
IOS_ROOT = _os.environ.get("IOS_ROOT", r"E:\ios漏洞")
QIANKE_SRC = _os.environ.get("QIANKE_SRC", r"E:\潜客")
import os

CONTENT = r'''-- ============================================================================
-- §4.2.5 隐藏脚手架菜单
-- ============================================================================
-- ★ 结论依据（实测，纯净库，未执行任何脚本）：
--   脚手架相关菜单共 15 条，其中 **只有 4 条顶层已 hidden=1**，
--   **11 条子菜单仍 hidden=0**：
--       excel, upload, breakpoint, customer, simpleUploader            (parent=9  example)
--       autoCode, formCreate, system, autoCodeAdmin, autoPkg, autoPlug (parent=14 systemTools)
--
--   前端过滤逻辑（src/pinia/modules/router.js L12）：
--       if ((!item.children || item.children.every(ch => ch.hidden))
--           && item.name !== '404' && !item.hidden) { ...隐藏该菜单... }
--   → **父菜单只有在【全部子菜单都 hidden】时才会被隐藏**。
--   既然有 11 个子菜单可见，父菜单的 hidden=1 不足以真正屏蔽这一组。
--   ⇒ 故本脚本**确有必要**：必须把子菜单一并隐藏。
--
-- ★ 两次自我更正（记录备查，均为实测驱动）：
--   ① 我曾误判"源数据已全部隐藏、本脚本冗余"——那是查了**被本脚本改过的库**，
--      测的是"改后"而非"源"。改用纯净库复测得 4 hidden / 11 visible。
--      **教训：验证"源状态"必须用从未被改动过的库。**
--   ② 首版备份表用 `DROP TABLE IF EXISTS ... ; CREATE TABLE ... AS SELECT`，
--      导致**第 2 次执行时把备份覆盖为"已隐藏"状态**，
--      回滚因此失效（实测 rollback 后仍 15/0）。
--      现改为 **CREATE TABLE IF NOT EXISTS**：备份**只建一次**，永不覆盖。
--
-- 幂等：备份只建一次；UPDATE 幂等。
-- 回滚：见文件末尾（基于备份表精确还原）。
--
-- 用法：
--   mysql -u<user> -p<pass> <db> < 20-hide-scaffold-menus.sql
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 步骤 0：备份原 hidden 值 —— ★ 只建一次，绝不覆盖
-- ---------------------------------------------------------------------------
-- 注：DROP 段保留但默认注释，仅在需要"重置备份"时手动启用。
-- DROP TABLE IF EXISTS `_bak_sys_base_menus_hidden`;

CREATE TABLE IF NOT EXISTS `_bak_sys_base_menus_hidden` AS
  SELECT `id`, `hidden`, NOW() AS `backed_up_at` FROM `sys_base_menus`
   WHERE 1=0;   -- 仅建结构

INSERT INTO `_bak_sys_base_menus_hidden` (`id`, `hidden`, `backed_up_at`)
  SELECT m.`id`, m.`hidden`, NOW()
    FROM `sys_base_menus` m
   WHERE NOT EXISTS (SELECT 1 FROM `_bak_sys_base_menus_hidden` b WHERE b.`id` = m.`id`);

SELECT '--- 备份表状态（应等于菜单总数，且重复执行不变）---' AS section;
SELECT COUNT(*) AS backed_up FROM `_bak_sys_base_menus_hidden`;

-- ---------------------------------------------------------------------------
-- 步骤 1：隐藏顶层脚手架 + 外链
-- ---------------------------------------------------------------------------
UPDATE `sys_base_menus` SET `hidden` = 1
 WHERE `id` IN (2, 9, 14, 22)
    OR `name` IN ('about', 'example', 'systemTools')
    OR `path` LIKE 'https://www.gin-vue-admin.com%';

-- ---------------------------------------------------------------------------
-- 步骤 2：隐藏脚手架的子菜单（★ 关键 —— 顶层隐藏不足以屏蔽整组）
-- ---------------------------------------------------------------------------
UPDATE `sys_base_menus` SET `hidden` = 1
 WHERE `parent_id` IN ('9', '14')
    OR `component` LIKE 'view/example/%'
    OR `component` LIKE 'view/systemTools/%';

-- ---------------------------------------------------------------------------
-- 验收 1：仍可见的脚手架项（期望 0 行）
-- ---------------------------------------------------------------------------
SELECT '--- 仍未隐藏的脚手架项（期望 0 行）---' AS section;
SELECT `id`, `name`, `component`, `hidden`
  FROM `sys_base_menus`
 WHERE (`name` IN ('about', 'example', 'systemTools')
     OR `component` LIKE 'view/example/%'
     OR `component` LIKE 'view/systemTools/%')
   AND (`hidden` = 0 OR `hidden` IS NULL);

-- ---------------------------------------------------------------------------
-- 验收 2：业务菜单未受影响（期望全部 hidden=0）
-- ---------------------------------------------------------------------------
SELECT '--- 业务菜单（id>=28，期望 hidden=0）---' AS section;
SELECT `id`, `name`, `title`, `hidden`
  FROM `sys_base_menus`
 WHERE `id` >= 28 AND `menu_level` = 0
 ORDER BY `id`;

-- ---------------------------------------------------------------------------
-- 验收 3：与备份表比对，本次实际改动条数（期望 11）
-- ---------------------------------------------------------------------------
SELECT '--- 本次改动条数（期望 11）---' AS section;
SELECT COUNT(*) AS changed
  FROM `sys_base_menus` m
  JOIN `_bak_sys_base_menus_hidden` b ON b.`id` = m.`id`
 WHERE m.`hidden` <> b.`hidden` OR (m.`hidden` IS NULL) <> (b.`hidden` IS NULL);

-- ============================================================================
-- 回滚（用备份表精确还原，不写死值）
-- ============================================================================
-- UPDATE `sys_base_menus` m
--   JOIN `_bak_sys_base_menus_hidden` b ON b.`id` = m.`id`
--    SET m.`hidden` = b.`hidden`;
--
-- ★ 前置条件：备份表须为"改动前"的快照。
--   因步骤 0 已改为 CREATE TABLE IF NOT EXISTS + 补插，重复执行不会覆盖，
--   故备份始终是首次执行前的状态。
--   若曾用旧版脚本（会覆盖备份），需先手工确认备份表内容。
--
-- ★ 为何不用固定值回滚：
--   源数据中 id=1(dashboard)/8(person)/25(autoCodeEdit) 原本就是 hidden=1，
--   若回滚写 `SET hidden=0 WHERE id IN (2,9,14,22)`，会把本就隐藏的项**误改为可见**。
-- ============================================================================
'''

fp = IOS_ROOT + r'\_integration\build\db-migration\20-hide-scaffold-menus.sql'
with open(fp, 'w', encoding='utf-8', newline='') as f:
    f.write(CONTENT)
print('written: %s (%d lines)' % (fp, CONTENT.count('\n') + 1))
