-- ============================================================================
-- 22-hide-prototype-shells.sql —— 下架三个"原型壳"页面（D-02b）
-- ============================================================================
-- ★ Owner 裁决 A（2026-10-02）：**从菜单下架**（一行 SQL，可逆）
--
-- ★ 依据：审核 D 的 D-02b 实测 —— 三个页面是【无数据源的原型壳】：
--   · customerfinance     | 84 | 客户财务   | 98 字节，整页只渲染字面量 "111"
--   · commissionsettings  | 86 | 佣金设置   | 3 输入框 + 写死的假地址，按钮无 @click
--   · currencysettings    | 87 | 货币设置   | 4 输入框，无保存按钮、无 API
--   ★ 三页均【无 @/api 导入、无 onMounted】⇒ 能正常打开、不报错
--     ⇒ 任何构建/启动/冒烟检查都发现不了
--
-- ★ 为何下架而非实现：
--   ① 实现它们需要【业务定义】（佣金规则 / 货币配置语义）⇒ Owner 层产品决策
--   ② "111" 无论选哪个方案都必须删（调试残留）
--   ③ 上线的界面不应有"点了没用"的页
--
-- ★ 幂等：备份只建一次；UPDATE 幂等。
-- ★ 回滚：见文件末尾（基于备份表精确还原）。
--
-- 用法：
--   mysql -h 127.0.0.1 -P 13306 -u root qk_e2e < 22-hide-prototype-shells.sql
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 步骤 0：备份（★ 复用 T26 的表，只建一次绝不覆盖）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `_bak_sys_base_menus_hidden_t26` AS
  SELECT `id`, `hidden`, NOW() AS `backed_up_at` FROM `sys_base_menus` WHERE 1=0;

-- ★ 注意：T26 已备份过全部 34 条；此处仅确保【本脚本涉及的 3 条】在表中
INSERT INTO `_bak_sys_base_menus_hidden_t26` (`id`, `hidden`, `backed_up_at`)
  SELECT m.`id`, m.`hidden`, NOW()
    FROM `sys_base_menus` m
   WHERE m.`id` IN (84, 86, 87)
     AND NOT EXISTS (
         SELECT 1 FROM `_bak_sys_base_menus_hidden_t26` b WHERE b.`id` = m.`id`
     );

SELECT '--- 备份表状态 ---' AS section;
SELECT COUNT(*) AS backed_up_total FROM `_bak_sys_base_menus_hidden_t26`;
SELECT `id`, `hidden` FROM `_bak_sys_base_menus_hidden_t26`
 WHERE `id` IN (84, 86, 87) ORDER BY `id`;

-- ---------------------------------------------------------------------------
-- 步骤 1：下架三个原型壳（★ 用 path 判据，不依赖 id；且限定标题以防误伤）
-- ---------------------------------------------------------------------------
UPDATE `sys_base_menus` SET `hidden` = 1
 WHERE `path` = 'customerfinance'
    OR `path` = 'commissionsettings'
    OR `path` = 'currencysettings';

SELECT '--- 步骤1 影响行数（期望 3）---' AS section;
SELECT ROW_COUNT() AS affected;

-- ---------------------------------------------------------------------------
-- 验收
-- ---------------------------------------------------------------------------
SELECT '--- 验收1：三个原型壳应已隐藏（期望 3 行 hidden=1）---' AS section;
SELECT `id`, `path`, `title`, `hidden`
  FROM `sys_base_menus`
 WHERE `path` IN ('customerfinance', 'commissionsettings', 'currencysettings')
 ORDER BY `id`;

SELECT '--- 验收2：hidden 分布（改前 0:31 / 1:3 ⇒ 期望 0:28 / 1:6）---' AS section;
SELECT `hidden`, COUNT(*) AS n FROM `sys_base_menus` GROUP BY `hidden`;

SELECT '--- 验收3：业务菜单未误伤（顶层应仍可见）---' AS section;
SELECT `id`, `path`, `title`, `hidden` FROM `sys_base_menus`
 WHERE `parent_id` = '0' AND `path` NOT IN ('about')
 ORDER BY `sort`;

SELECT '--- 验收4：被隐藏的 3 页确认（应无其它页面被误伤）---' AS section;
SELECT COUNT(*) AS newly_hidden FROM `sys_base_menus`
 WHERE `hidden` = 1
   AND `id` IN (SELECT `id` FROM `_bak_sys_base_menus_hidden_t26` WHERE `hidden` = 0);

-- ============================================================================
-- 回滚（需要时手动执行）：
--   UPDATE `sys_base_menus` m
--     JOIN `_bak_sys_base_menus_hidden_t26` b ON b.`id` = m.`id`
--      SET m.`hidden` = b.`hidden`;
--   ★ 注意：这会一并还原 T26 的 about 隐藏（若需保留，改为只还原 84/86/87）：
--   UPDATE `sys_base_menus` SET `hidden` = 0 WHERE `id` IN (84, 86, 87);
-- ============================================================================
