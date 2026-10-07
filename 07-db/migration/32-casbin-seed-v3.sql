-- ============================================================================
-- R2-2 · casbin seed v3（★ 从【运行时路由表】生成）
-- ============================================================================
-- Owner 裁决 A：888（超级管理员）→ 全部；9528（普通用户）→ 只读 GET
--
-- ★ v3 与 v2 的区别：
--   v2 用 router/*.go 的【正则提取】⇒ 漏 20 条、方法不匹配 4 条；
--   v3 用 Go 启动日志的 [GIN-debug] 行 ⇒ 运行时【真实注册】的路由。
--
-- ★ 排除（不经 CasbinHandler）：
--   /base/*（PublicGroup 匿名）、/app/*（ServiceTokenAuth）、
--   /init/*（PublicGroup）、/uploads/*、/form-generator/*、/health
--
-- ★ 幂等：INSERT ... SELECT ... WHERE NOT EXISTS
-- ============================================================================

-- ---- 步骤 1：sys_apis ----
INSERT INTO `sys_apis` (`created_at`, `updated_at`, `path`, `api_group`, `method`)
SELECT NOW(), NOW(), src.p, src.g, src.m FROM (
    SELECT '/api/createApi' AS p, 'api' AS g, 'POST' AS m
    UNION ALL SELECT '/api/deleteApi' AS p, 'api' AS g, 'POST' AS m
    UNION ALL SELECT '/api/deleteApisByIds' AS p, 'api' AS g, 'DELETE' AS m
    UNION ALL SELECT '/api/getAllApis' AS p, 'api' AS g, 'POST' AS m
    UNION ALL SELECT '/api/getApiById' AS p, 'api' AS g, 'POST' AS m
    UNION ALL SELECT '/api/getApiList' AS p, 'api' AS g, 'POST' AS m
    UNION ALL SELECT '/api/updateApi' AS p, 'api' AS g, 'POST' AS m
    UNION ALL SELECT '/authority/copyAuthority' AS p, 'authority' AS g, 'POST' AS m
    UNION ALL SELECT '/authority/createAuthority' AS p, 'authority' AS g, 'POST' AS m
    UNION ALL SELECT '/authority/deleteAuthority' AS p, 'authority' AS g, 'POST' AS m
    UNION ALL SELECT '/authority/getAuthorityList' AS p, 'authority' AS g, 'POST' AS m
    UNION ALL SELECT '/authority/setDataAuthority' AS p, 'authority' AS g, 'POST' AS m
    UNION ALL SELECT '/authority/updateAuthority' AS p, 'authority' AS g, 'PUT' AS m
    UNION ALL SELECT '/authorityBtn/canRemoveAuthorityBtn' AS p, 'authorityBtn' AS g, 'POST' AS m
    UNION ALL SELECT '/authorityBtn/getAuthorityBtn' AS p, 'authorityBtn' AS g, 'POST' AS m
    UNION ALL SELECT '/authorityBtn/setAuthorityBtn' AS p, 'authorityBtn' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/createPackage' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/createPlug' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/createTemp' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/delPackage' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/delSysHistory' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/getColumn' AS p, 'autoCode' AS g, 'GET' AS m
    UNION ALL SELECT '/autoCode/getDB' AS p, 'autoCode' AS g, 'GET' AS m
    UNION ALL SELECT '/autoCode/getMeta' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/getPackage' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/getSysHistory' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/getTables' AS p, 'autoCode' AS g, 'GET' AS m
    UNION ALL SELECT '/autoCode/preview' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/autoCode/rollback' AS p, 'autoCode' AS g, 'POST' AS m
    UNION ALL SELECT '/casbin/getPolicyPathByAuthorityId' AS p, 'casbin' AS g, 'POST' AS m
    UNION ALL SELECT '/casbin/updateCasbin' AS p, 'casbin' AS g, 'POST' AS m
    UNION ALL SELECT '/device/add_agent' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/add_commission_address' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/add_packet' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/add_payment_address' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/agent_device_list' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/agent_financial' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/agent_list' AS p, 'device' AS g, 'GET' AS m
    UNION ALL SELECT '/device/agent_payment_address' AS p, 'device' AS g, 'GET' AS m
    UNION ALL SELECT '/device/agent_tabulation' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/agent_wallet_list' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/copy_private' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/custom_financial' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/custom_wallet_list' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/financial' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/get_index_info' AS p, 'device' AS g, 'GET' AS m
    UNION ALL SELECT '/device/get_packet_info' AS p, 'device' AS g, 'GET' AS m
    UNION ALL SELECT '/device/hf' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/list' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/modify_commission_address' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/modify_payment_address' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/packet_list' AS p, 'device' AS g, 'GET' AS m
    UNION ALL SELECT '/device/payment_address' AS p, 'device' AS g, 'GET' AS m
    UNION ALL SELECT '/device/private_wallet_list' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/rk' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/shougei' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/system_address' AS p, 'device' AS g, 'GET' AS m
    UNION ALL SELECT '/device/token_list' AS p, 'device' AS g, 'GET' AS m
    UNION ALL SELECT '/device/update_wallet_balance' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/wallet_balance_list' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/device/wallet_list' AS p, 'device' AS g, 'POST' AS m
    UNION ALL SELECT '/jwt/jsonInBlacklist' AS p, 'jwt' AS g, 'POST' AS m
    UNION ALL SELECT '/menu/addBaseMenu' AS p, 'menu' AS g, 'POST' AS m
    UNION ALL SELECT '/menu/addMenuAuthority' AS p, 'menu' AS g, 'POST' AS m
    UNION ALL SELECT '/menu/deleteBaseMenu' AS p, 'menu' AS g, 'POST' AS m
    UNION ALL SELECT '/menu/getBaseMenuById' AS p, 'menu' AS g, 'POST' AS m
    UNION ALL SELECT '/menu/getBaseMenuTree' AS p, 'menu' AS g, 'POST' AS m
    UNION ALL SELECT '/menu/getMenu' AS p, 'menu' AS g, 'POST' AS m
    UNION ALL SELECT '/menu/getMenuAuthority' AS p, 'menu' AS g, 'POST' AS m
    UNION ALL SELECT '/menu/getMenuList' AS p, 'menu' AS g, 'POST' AS m
    UNION ALL SELECT '/menu/updateBaseMenu' AS p, 'menu' AS g, 'POST' AS m
    UNION ALL SELECT '/sysDictionary/createSysDictionary' AS p, 'sysDictionary' AS g, 'POST' AS m
    UNION ALL SELECT '/sysDictionary/deleteSysDictionary' AS p, 'sysDictionary' AS g, 'DELETE' AS m
    UNION ALL SELECT '/sysDictionary/findSysDictionary' AS p, 'sysDictionary' AS g, 'GET' AS m
    UNION ALL SELECT '/sysDictionary/getSysDictionaryList' AS p, 'sysDictionary' AS g, 'GET' AS m
    UNION ALL SELECT '/sysDictionary/updateSysDictionary' AS p, 'sysDictionary' AS g, 'PUT' AS m
    UNION ALL SELECT '/sysDictionaryDetail/createSysDictionaryDetail' AS p, 'sysDictionaryDetail' AS g, 'POST' AS m
    UNION ALL SELECT '/sysDictionaryDetail/deleteSysDictionaryDetail' AS p, 'sysDictionaryDetail' AS g, 'DELETE' AS m
    UNION ALL SELECT '/sysDictionaryDetail/findSysDictionaryDetail' AS p, 'sysDictionaryDetail' AS g, 'GET' AS m
    UNION ALL SELECT '/sysDictionaryDetail/getSysDictionaryDetailList' AS p, 'sysDictionaryDetail' AS g, 'GET' AS m
    UNION ALL SELECT '/sysDictionaryDetail/updateSysDictionaryDetail' AS p, 'sysDictionaryDetail' AS g, 'PUT' AS m
    UNION ALL SELECT '/sysOperationRecord/createSysOperationRecord' AS p, 'sysOperationRecord' AS g, 'POST' AS m
    UNION ALL SELECT '/sysOperationRecord/deleteSysOperationRecord' AS p, 'sysOperationRecord' AS g, 'DELETE' AS m
    UNION ALL SELECT '/sysOperationRecord/deleteSysOperationRecordByIds' AS p, 'sysOperationRecord' AS g, 'DELETE' AS m
    UNION ALL SELECT '/sysOperationRecord/findSysOperationRecord' AS p, 'sysOperationRecord' AS g, 'GET' AS m
    UNION ALL SELECT '/sysOperationRecord/getSysOperationRecordList' AS p, 'sysOperationRecord' AS g, 'GET' AS m
    UNION ALL SELECT '/system/getServerInfo' AS p, 'system' AS g, 'POST' AS m
    UNION ALL SELECT '/system/getSystemConfig' AS p, 'system' AS g, 'POST' AS m
    UNION ALL SELECT '/system/reloadSystem' AS p, 'system' AS g, 'POST' AS m
    UNION ALL SELECT '/system/setSystemConfig' AS p, 'system' AS g, 'POST' AS m
    UNION ALL SELECT '/user/admin_register' AS p, 'user' AS g, 'POST' AS m
    UNION ALL SELECT '/user/changePassword' AS p, 'user' AS g, 'POST' AS m
    UNION ALL SELECT '/user/deleteUser' AS p, 'user' AS g, 'DELETE' AS m
    UNION ALL SELECT '/user/getUserInfo' AS p, 'user' AS g, 'GET' AS m
    UNION ALL SELECT '/user/getUserList' AS p, 'user' AS g, 'POST' AS m
    UNION ALL SELECT '/user/resetPassword' AS p, 'user' AS g, 'POST' AS m
    UNION ALL SELECT '/user/setSelfInfo' AS p, 'user' AS g, 'PUT' AS m
    UNION ALL SELECT '/user/setUserAuthorities' AS p, 'user' AS g, 'POST' AS m
    UNION ALL SELECT '/user/setUserAuthority' AS p, 'user' AS g, 'POST' AS m
    UNION ALL SELECT '/user/setUserInfo' AS p, 'user' AS g, 'PUT' AS m
  ) AS src
 WHERE NOT EXISTS (
     SELECT 1 FROM `sys_apis` a WHERE a.`path` = src.p AND a.`method` = src.m
 );

SELECT '--- sys_apis 总数 ---' AS section;
SELECT COUNT(*) AS n FROM `sys_apis`;

-- ---- 步骤 2：casbin_rule ----
-- 888：全部
INSERT INTO `casbin_rule` (`p_type`, `v0`, `v1`, `v2`)
SELECT 'p', '888', a.`path`, a.`method` FROM `sys_apis` a
 WHERE NOT EXISTS (
   SELECT 1 FROM `casbin_rule` c WHERE c.`p_type`='p' AND c.`v0`='888'
     AND c.`v1`=a.`path` AND c.`v2`=a.`method`);

-- 9528：只读（GET）
INSERT INTO `casbin_rule` (`p_type`, `v0`, `v1`, `v2`)
SELECT 'p', '9528', a.`path`, a.`method` FROM `sys_apis` a
 WHERE a.`method`='GET' AND NOT EXISTS (
   SELECT 1 FROM `casbin_rule` c WHERE c.`p_type`='p' AND c.`v0`='9528'
     AND c.`v1`=a.`path` AND c.`v2`=a.`method`);

SELECT '--- casbin_rule 统计 ---' AS section;
SELECT `v0` AS role, `v2` AS method, COUNT(*) AS n FROM `casbin_rule`
 WHERE `p_type`='p' GROUP BY `v0`, `v2` ORDER BY `v0`, `v2`;

-- ---- 验收 ----
SELECT '--- 验收1：888 覆盖率 ---' AS section;
SELECT (SELECT COUNT(*) FROM `sys_apis`) AS apis_total,
       (SELECT COUNT(*) FROM `casbin_rule` WHERE `p_type`='p' AND `v0`='888') AS granted_888;
SELECT '--- 验收2：9528 只读 ---' AS section;
SELECT `v2` AS method, COUNT(*) AS n FROM `casbin_rule`
 WHERE `p_type`='p' AND `v0`='9528' GROUP BY `v2`;
SELECT '--- 验收3：无 1234 ---' AS section;
SELECT COUNT(*) AS n_1234 FROM `casbin_rule` WHERE `v0`='1234';
