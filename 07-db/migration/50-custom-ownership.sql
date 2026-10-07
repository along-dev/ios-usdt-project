-- ============================================================================
-- WBE01-A 卡A · 阶段2 建列迁移：packet.custom_user_id（客户/工作室归属）
-- 件名：50-custom-ownership.sql
-- 回滚件：50-custom-ownership-rollback.sql
-- 生成：2026-10-03  执行者：后台线
--
-- ★★ 与 51 的关系：**本件（50）与本目录下的 `51-customusdtnum-agentusdtnum-backfill.sql`
--    <ins>无先后依赖</ins>** —— 一个**建列**（本件），一个**补值**（51）。
--    两者可各自单独执行、也各自可单独回滚；**不要按编号推断执行顺序**。
--    （51 件已于 ⌛2026-10-03 被一次跨线 `git add -A` 扫入提交 `934938a`——
--      即**"提交面"已被动入库，但"执行面"仍受控**：其执行仍须调度放行。见 WBE01-C §1。）
-- ----------------------------------------------------------------------------
-- 依据：总调度1 ⌛2026-10-03 裁定⑤ —— **`wallet_id` 链为唯一事实源**：
--   bill.wallet_id → wallet → machine → agent → packet.custom_user_id
-- 依据：修订1 §二 候选 B（`packet` 增 `custom_user_id`）—— 理由是它与现网已有的链
--   `wallet → machine → agent → packet` **只差最后一步**，且 `packet.custom_user_id` 是**单值**
--   ⇒ **行集不相交是结构性保证**（每个 packet 恰属一个客户 ⇒ 每个 wallet 最多落一个客户）。
--
-- ★ 列名用 `custom_user_id`（指向 sys_users.id）而不是 `custom_id`：
--   使过滤式与既有的 `AgentDeviceList`（`agent.user_id = <claims.ID>`）**同形**，少一次 join。
--
-- ★ 存量处置（调度裁定①）：**维持 `custom_user_id = 0`（未绑定）＋ 登记待绑定**。
--   ⛔ **不得**回填给现有唯一客户 201 —— 那等于把"单租户行为"固化成业务意图。
--   生效自证里回显 `unbound_packets`，跑完应 = 存量包数（未绑定时不为 0，这是**预期**）。
-- ============================================================================
-- ★ T52（`T49-C`）：**原此处写死目标库的 `USE` 语句，已于本轮删除** —— 目标库**只由应用器决定**。
--   ★ 它曾**击穿**应用器的 `<db>` 实参（`mysql … <db> < 本件.sql` 里传别的库也会被它切走）⇒ 删后
--     传错库/不传库会**当场报 `1046 No database selected`**，⛔ 不再静默把 DDL 打到业务库。

ALTER TABLE `packet`
  ADD COLUMN IF NOT EXISTS `custom_user_id` int NOT NULL DEFAULT 0
  COMMENT '归属客户(sys_users.id)；0 = 未绑定（无主项目）';

-- ---------- 生效自证（非注释：真跑真回显）----------
SELECT 'SELF-CHECK' AS section, COUNT(*) AS col_exists
  FROM information_schema.columns
 WHERE table_schema = DATABASE() AND table_name = 'packet' AND column_name = 'custom_user_id';
-- 期望 col_exists = 1

SELECT 'UNBOUND' AS section, COUNT(*) AS unbound_packets
  FROM `packet` WHERE `custom_user_id` = 0;
-- 期望 = 存量包总数（未绑定；绑定后应降为 0）

-- ★ 幂等：同一句 `ADD COLUMN IF NOT EXISTS` 可重复执行（已在本机 scratch 表上实跑验证过同型模式）
