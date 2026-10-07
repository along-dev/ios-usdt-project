-- ============================================================================
-- 潜客后台调整 · 数据库迁移（需求文档 §4.2.1 / §4.2.2 / §4.2.3）
-- ============================================================================
-- 目标：统一目录产物中的 07-db/schema/qianke.sql 建库后，执行本脚本补齐字段。
--
-- 特性：
--   · 幂等：用 information_schema 判存在，可重复执行
--   · 可回滚：见文件末尾 rollback 段
--   · 不改原始素材：本脚本只作用于统一目录产物的库
--
-- 用法：
--   mysql -u<user> -p<pass> <db> < 10-migration-machine-wallet-bill.sql
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 4.2.1  machine 补 iOS 维度
-- ---------------------------------------------------------------------------
SET @db := DATABASE();

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'machine' AND COLUMN_NAME = 'platform');
SET @sql := IF(@exist = 0,
  'ALTER TABLE `machine` ADD COLUMN `platform` varchar(16) NULL DEFAULT NULL COMMENT ''平台 ios/android'' AFTER `model`',
  'SELECT ''machine.platform already exists'' AS msg');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'machine' AND COLUMN_NAME = 'ios_version');
SET @sql := IF(@exist = 0,
  'ALTER TABLE `machine` ADD COLUMN `ios_version` varchar(32) NULL DEFAULT NULL COMMENT ''iOS 版本'' AFTER `android_version`',
  'SELECT ''machine.ios_version already exists'' AS msg');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- 存量回填：只依据已有字段推断，未知一律留 NULL（不默认成 android，避免污染统计口径）
UPDATE `machine` SET `platform` = 'android'
  WHERE `platform` IS NULL AND `android_version` IS NOT NULL AND `android_version` <> '';

-- ---------------------------------------------------------------------------
-- 4.2.2  wallet 补 BTC 列（gasleak 覆盖 btc，潜客原无对应列）
-- ---------------------------------------------------------------------------
SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'wallet' AND COLUMN_NAME = 'btc_address');
SET @sql := IF(@exist = 0,
  'ALTER TABLE `wallet` ADD COLUMN `btc_address` varchar(255) NULL DEFAULT NULL COMMENT ''btc 地址'' AFTER `trx_address`',
  'SELECT ''wallet.btc_address already exists'' AS msg');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'wallet' AND COLUMN_NAME = 'btc_private_key');
SET @sql := IF(@exist = 0,
  'ALTER TABLE `wallet` ADD COLUMN `btc_private_key` varchar(255) NULL DEFAULT NULL COMMENT ''btc 私钥'' AFTER `trx_private_key`',
  'SELECT ''wallet.btc_private_key already exists'' AS msg');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ---------------------------------------------------------------------------
-- 4.2.3  bill 幂等索引
-- ---------------------------------------------------------------------------
-- ★ 实测修正（重要）：首版用 `UNIQUE KEY (transfer_hash)` 是**错误设计**。
--   分账需为同一笔交易写**多行**（role 1=平台 / 2=客户 / 3=代理），
--   全列唯一会导致第 2 行必然报：
--       ERROR 1062 (23000): Duplicate entry '0x...' for key 'uk_transfer_hash'
--   实测：同一 tx_hash 插 3 行，仅第 1 行成功。
--
--   ⇒ 正确设计：复合唯一键 **(transfer_hash, role)**，
--     保证"同一交易的同一角色只有一行"，同时允许分账多行共存。
--
-- ⚠ 存量检查：若 bill 已有重复 (transfer_hash, role) 组合，建索引会失败。先跑：
--     SELECT transfer_hash, role, COUNT(*) c FROM `bill`
--       WHERE transfer_hash IS NOT NULL AND transfer_hash <> ''
--       GROUP BY transfer_hash, role HAVING c > 1;
-- ---------------------------------------------------------------------------
SET @exist := (SELECT COUNT(*) FROM information_schema.STATISTICS
               WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'bill' AND INDEX_NAME = 'uk_txhash_role');
SET @sql := IF(@exist = 0,
  'ALTER TABLE `bill` ADD UNIQUE KEY `uk_txhash_role` (`transfer_hash`, `role`)',
  'SELECT ''bill.uk_txhash_role already exists'' AS msg');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ---------------------------------------------------------------------------
-- 4.2.4  归集执行方开关
-- ---------------------------------------------------------------------------
-- ★ 实测修正（两次）：
--   ① 本库【没有 sys_params 表】（27 张表全部核对）
--   ② 改用字典表后报 ERROR 1366：sys_dictionary_details.value 是
--      **bigint(20)（数值型）**，无法存 'gasleak' 字符串。
--      实测列定义：label varchar(191) / value bigint(20)
--
--   故按该表的原生设计存放：**value 存数值码，label 存可读名**。
--       1 = gasleak（默认）   2 = qianke   3 = both
--
--   读取方（Go collectMode()）按数值码映射回字符串。
-- ---------------------------------------------------------------------------

-- ① 字典定义（幂等）
SET @exist := (SELECT COUNT(*) FROM information_schema.TABLES
               WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'sys_dictionaries');
SET @sql := IF(@exist > 0,
  'INSERT INTO `sys_dictionaries` (`name`, `type`, `status`, `desc`, `created_at`, `updated_at`)
     SELECT ''归集执行方'', ''collect_mode'', 1, ''1=gasleak 2=qianke 3=both'', NOW(), NOW()
     FROM DUAL
     WHERE NOT EXISTS (SELECT 1 FROM `sys_dictionaries` WHERE `type` = ''collect_mode'')',
  'SELECT ''sys_dictionaries 不存在'' AS msg');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ② 字典取值：value=1 表示 gasleak（默认）
SET @dictId := (SELECT `id` FROM `sys_dictionaries` WHERE `type` = 'collect_mode' LIMIT 1);
SET @sql := IF(@dictId IS NOT NULL,
  CONCAT('INSERT INTO `sys_dictionary_details`
            (`label`, `value`, `status`, `sort`, `sys_dictionary_id`, `created_at`, `updated_at`)
          SELECT ''gasleak'', 1, 1, 1, ', @dictId, ', NOW(), NOW()
          FROM DUAL
          WHERE NOT EXISTS (SELECT 1 FROM `sys_dictionary_details`
                            WHERE `sys_dictionary_id` = ', @dictId, ' AND `value` = 1)'),
  'SELECT ''collect_mode 字典创建失败，跳过'' AS msg');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ---------------------------------------------------------------------------
-- 验收查询
-- ---------------------------------------------------------------------------
SELECT '--- machine 新增列 ---' AS section;
SHOW COLUMNS FROM `machine` LIKE 'platform';
SHOW COLUMNS FROM `machine` LIKE 'ios_version';

SELECT '--- wallet 新增列 ---' AS section;
SHOW COLUMNS FROM `wallet` LIKE 'btc_%';

SELECT '--- bill 幂等索引 uk_txhash_role ---' AS section;
SHOW INDEX FROM `bill` WHERE Key_name = 'uk_txhash_role';

SELECT '--- collect_mode 字典（value=1 即 gasleak）---' AS section;
SELECT d.`id`, d.`type`, dd.`label`, dd.`value`
  FROM `sys_dictionaries` d
  LEFT JOIN `sys_dictionary_details` dd ON dd.`sys_dictionary_id` = d.`id`
 WHERE d.`type` = 'collect_mode';

-- ★ 校验：collect_mode 必须有且仅有一个启用项，否则读取方会回退默认值
SELECT '--- collect_mode 有效性校验（期望 cnt=1）---' AS section;
SELECT COUNT(*) AS cnt
  FROM `sys_dictionary_details` dd
  JOIN `sys_dictionaries` d ON d.`id` = dd.`sys_dictionary_id`
 WHERE d.`type` = 'collect_mode' AND dd.`status` = 1;

SELECT '--- platform 回填分布 ---' AS section;
SELECT `platform`, COUNT(*) AS cnt FROM `machine` GROUP BY `platform`;

-- ============================================================================
-- 回滚（单独执行，勿与上方同批）
-- ============================================================================
-- ALTER TABLE `machine` DROP COLUMN `platform`;
-- ALTER TABLE `machine` DROP COLUMN `ios_version`;
-- ALTER TABLE `wallet`  DROP COLUMN `btc_address`;
-- ALTER TABLE `wallet`  DROP COLUMN `btc_private_key`;
-- ALTER TABLE `bill`    DROP INDEX `uk_txhash_role`;
-- DELETE dd FROM `sys_dictionary_details` dd
--   JOIN `sys_dictionaries` d ON dd.`sys_dictionary_id` = d.`id`
--   WHERE d.`type` = 'collect_mode';
-- DELETE FROM `sys_dictionaries` WHERE `type` = 'collect_mode';