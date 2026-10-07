-- ============================================================================
-- 40-prod-db-hardening.sql —— MariaDB 生产加固（加固清单 §一-1）
-- ============================================================================
-- ★ 性质：**部署期执行**。本脚本【不在装测环境运行】。
--   原因：装测环境依赖 `--skip-grant-tables` + 空口令；
--         执行本脚本会立刻切断装测环境的连接。
--
-- ★ Owner 裁决（R2-4 同类）：**写入清单，不在当前环境执行**。
--
-- ★ 执行前置：
--   ① MariaDB 已以【非 --skip-grant-tables】方式启动（会用到权限表）
--   ② 已备份数据库（mysqldump）
--   ③ 已确认应用能读取到新口令（08-infra/env.prod.example 的 MYSQL_PASSWORD）
--
-- ★ 执行方式：
--   mysql -h 127.0.0.1 -P 13306 -u root -p < 40-prod-db-hardening.sql
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 步骤 1：设 root 强口令
--   ★★ 占位符 <ROOT_PASSWORD> 必须替换为真实强口令后执行
-- ---------------------------------------------------------------------------
-- ALTER USER 'root'@'localhost'  IDENTIFIED BY '<ROOT_PASSWORD>';
-- ALTER USER 'root'@'127.0.0.1' IDENTIFIED BY '<ROOT_PASSWORD>';
-- ALTER USER 'root'@'::1'        IDENTIFIED BY '<ROOT_PASSWORD>';

-- ---------------------------------------------------------------------------
-- 步骤 2：建应用专用账号（★ 最小权限）
--   ★ 只授 SELECT/INSERT/UPDATE/DELETE，不授 DDL
-- ---------------------------------------------------------------------------
-- CREATE USER IF NOT EXISTS 'qk_app'@'127.0.0.1' IDENTIFIED BY '<APP_PASSWORD>';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON `qk_e2e`.* TO 'qk_app'@'127.0.0.1';

-- ★ 若应用还需读 information_schema（部分 ORM 需要）
-- GRANT SELECT ON `information_schema`.* TO 'qk_app'@'127.0.0.1';

-- ---------------------------------------------------------------------------
-- 步骤 3：清理匿名账号与测试库（★ 可选）
-- ---------------------------------------------------------------------------
-- DROP USER IF EXISTS ''@'localhost';
-- DROP USER IF EXISTS ''@'%';
-- DROP DATABASE IF EXISTS `test`;

-- ---------------------------------------------------------------------------
-- 步骤 4：收紧绑定（★ 在 my.cnf 中，不在 SQL）
-- ---------------------------------------------------------------------------
-- my.cnf:
--   [mysqld]
--   bind-address = 127.0.0.1
--   ★ 且【移除】skip-grant-tables

FLUSH PRIVILEGES;

-- ---------------------------------------------------------------------------
-- 验收（执行后核对）
-- ---------------------------------------------------------------------------
SELECT '--- 验收1：不要有匿名账号（期望 0 行）---' AS section;
SELECT User, Host FROM mysql.user WHERE User = '';

SELECT '--- 验收2：qk_app 的权限（应仅 DML）---' AS section;
SHOW GRANTS FOR 'qk_app'@'127.0.0.1';

SELECT '--- 验收3：全局状态 ---' AS section;
SELECT User, Host, plugin FROM mysql.user WHERE User IN ('root', 'qk_app');

-- ============================================================================
-- 回滚：
--   ALTER USER 'root'@'localhost' IDENTIFIED BY '';
--   DROP USER 'qk_app'@'127.0.0.1';
--   ★ 并以 --skip-grant-tables 重启
-- ============================================================================
